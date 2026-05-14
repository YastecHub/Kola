"""
model.py — trains the KOLA credit scoring model.

WHY XGBClassifier (NOT Regressor):
  Credit scoring is a classification problem at its core: will this member
  repay or not? XGBClassifier outputs a probability (0.0 to 1.0) that the
  member is creditworthy. We convert that probability to a 300-850 scale
  using the same formula credit bureaus use.

  Using a Regressor would mean we're predicting a score directly — but what
  does a "score" of 0.74 mean in absolute terms? Nothing, without a fixed
  scale. The Classifier's probability is the universal currency: 0.753 means
  "75.3% confident this person is creditworthy" — that's defensible to any
  judge or lender.

SCORE FORMULA:
  kola_score = int(300 + (probability × 550))

  300 = floor (no one gets a zero — there's always some baseline humanity)
  850 = ceiling (FICO maximum, aligns with lender expectations)
  550 = the range

  Probability 0.0 → score 300 (no history, high risk)
  Probability 0.5 → score 575 (average)
  Probability 0.753 → score 714 (Aminat — good but not perfect)
  Probability 1.0 → score 850 (perfect, rare)

WHY XGBoost SPECIFICALLY:
  1. Handles tabular data better than neural nets on small datasets
  2. Handles missing values natively (new member with no trade events = OK)
  3. SHAP (TreeExplainer) produces exact explanations — not approximations
  4. Fast: trains in seconds, scores in microseconds
  5. Interpretable enough to present to CBN or any regulator

SHAP EXPLAINABILITY:
  Every score comes with exactly 5 factors showing what drove it.
  TreeExplainer for XGBoost gives exact Shapley values — mathematically
  provable to be the only fair attribution method.
  We scale log-odds SHAP values to approximate score-point impact
  (how many of the 300-850 points each feature contributed).
"""

import json
import pickle
import numpy as np
import xgboost as xgb
import shap
from features import extract_features, FEATURE_NAMES, SHAP_KEYS


def build_training_data(dataset: list) -> tuple[np.ndarray, np.ndarray]:
    """
    Build X (features) and y (labels) from the 500-member dataset.

    Excludes new members (label=None) — they have insufficient history
    to provide a reliable training signal. We can still SCORE them at
    inference time; we just don't train on them.
    """
    from features import assign_label

    X, y = [], []
    for member in dataset:
        label = assign_label(member)
        if label is None:
            continue  # new members: excluded from training, scored at inference
        features = extract_features(member)
        X.append([features[f] for f in FEATURE_NAMES])
        y.append(label)

    print(f"Training set: {len(X)} members ({sum(y)} creditworthy, {len(y) - sum(y)} not)")
    return np.array(X, dtype=np.float32), np.array(y, dtype=np.float32)


def train() -> tuple:
    """
    Full training pipeline:
      1. Generate 500 synthetic members
      2. Extract features
      3. Train XGBClassifier
      4. Build SHAP TreeExplainer
      5. Save model and explainer to disk

    Returns: (model, explainer)
    """
    from synthetic import generate_dataset

    print("Generating 500-member training dataset...")
    dataset = generate_dataset()

    print("Extracting features...")
    X, y = build_training_data(dataset)

    model = xgb.XGBClassifier(
        n_estimators=300,       # 300 trees — more than a regressor needs because
                                # classification boundaries are harder to learn
        max_depth=4,            # shallow trees = less memorisation on small data
        learning_rate=0.05,     # small steps = more stable probability estimates
        subsample=0.8,          # each tree trains on 80% of data = prevents overfitting
        colsample_bytree=0.8,   # each tree sees 80% of features
        scale_pos_weight=1.0,   # balanced classes (125 reliable, 250 not) — adjust if needed
        eval_metric="logloss",  # binary cross-entropy: penalises confident wrong predictions
        use_label_encoder=False,
        random_state=42,
        verbosity=0,
    )

    model.fit(X, y)

    # Verify probability output works
    sample_probs = model.predict_proba(X[:5])
    print(f"Sample probabilities (class 1): {[round(p[1], 3) for p in sample_probs]}")

    # SHAP TreeExplainer: exact Shapley values for tree models
    # This is O(TLD) where T=trees, L=leaves, D=depth — fast on XGBoost
    explainer = shap.TreeExplainer(model)
    print("SHAP TreeExplainer built.")

    with open("kola_model.pkl", "wb") as f:
        pickle.dump(model, f)
    with open("kola_explainer.pkl", "wb") as f:
        pickle.dump(explainer, f)

    print("Saved: kola_model.pkl, kola_explainer.pkl")
    return model, explainer


def load_model() -> tuple:
    """Load pre-trained model and explainer from disk."""
    with open("kola_model.pkl", "rb") as f:
        model = pickle.load(f)
    with open("kola_explainer.pkl", "rb") as f:
        explainer = pickle.load(f)
    return model, explainer


def score_member(member: dict, model, explainer) -> dict:
    """
    Score one Ajo member. This is what POST /score calls.

    Returns the exact PRD contract:
    {
      "score": 714,
      "probability": 0.753,
      "shap": {
        "streak": 18,
        "catchup": 8,
        "amount_std": -6,
        "collector": 4,
        "trade": 12
      },
      "anomaly_flag": false,    # set by api.py, not here
      "anomaly_reason": null    # set by api.py, not here
    }
    """
    features = extract_features(member)
    X = np.array([[features[f] for f in FEATURE_NAMES]], dtype=np.float32)

    # XGBClassifier.predict_proba returns [[p_class0, p_class1]]
    probability = float(model.predict_proba(X)[0][1])
    probability = round(max(0.0, min(1.0, probability)), 4)

    # The KOLA Score formula — same range as FICO for lender familiarity
    kola_score = int(300 + (probability * 550))

    # ── SHAP EXPLANATION ──────────────────────────────────────────────────────
    # TreeExplainer for XGBClassifier returns SHAP values in log-odds space.
    # For binary classification, shap_values may be:
    #   - A 2D array (n_samples, n_features) for the positive class, or
    #   - A list of two arrays [class0_shap, class1_shap]
    # We always want class 1 (creditworthy) SHAP values.
    raw_shap = explainer.shap_values(X)

    if isinstance(raw_shap, list):
        # Older SHAP versions: list of [class0, class1]
        shap_vals = raw_shap[1][0]
    else:
        # Newer SHAP versions: single array for positive class
        shap_vals = raw_shap[0]

    # Convert log-odds SHAP to approximate score-point impact.
    # At probability p, the score sensitivity to log-odds is p*(1-p)*550.
    # We use the actual probability for accuracy.
    sensitivity = probability * (1.0 - probability) * 550

    shap_output = {}
    for i, shap_key in enumerate(SHAP_KEYS):
        raw_val = float(shap_vals[i])
        # Convert to approximate score points, round to integer for clean display
        score_pts = int(round(raw_val * sensitivity))
        shap_output[shap_key] = score_pts

    return {
        "score": kola_score,
        "probability": probability,
        "shap": shap_output,
    }


if __name__ == "__main__":
    import random as _rand
    _rand.seed(99)

    model, explainer = train()

    # Verify model learned correctly: score each archetype
    from synthetic import generate_dataset as _gen
    from features import assign_label as _label
    _ds = _gen()

    print("\n=== ARCHETYPE SANITY CHECK ===")
    for arch in ["reliable", "inconsistent", "gaming"]:
        members = [m for m in _ds if m["archetype"] == arch][:20]
        scores = [score_member(m, model, explainer)["score"] for m in members]
        avg = sum(scores) / len(scores)
        print(f"  {arch:15s}: avg score = {avg:.0f}  (range {min(scores)}-{max(scores)})")

    # Aminat's profile — amounts vary slightly (real Ajo has natural variation)
    # Week 7 was 3 days late. She is a collector. Two supplier payments.
    aminat_amounts = [5200, 4900, 5000, 5100, 4800, 5000, 5300, 4700, 5100, 4900, 5000, 5200, 4800]
    aminat = {
        "member_id": "aminat-001",
        "name": "Aminat Ibrahim",
        "archetype": "reliable",
        "collector_trust": 1,
        "events": [
            *[{
                "type": "contribution",
                "week": w,
                "amount": aminat_amounts[w - 1],
                "date": f"2025-{str(w).zfill(2)}-07",
                "days_late": 3 if w == 7 else 0,
                "verified": True,
                "sender_id": "aminat-001",
                "receiver_id": "collector-mama"
            } for w in range(1, 14)],
            {
                "type": "trade",
                "week": None,
                "amount": 47500,
                "date": "2025-05-05",
                "days_late": 0,
                "counterparty_nuban": "9034512987",
                "verified": True,
                "sender_id": "aminat-001",
                "receiver_id": "9034512987"
            },
            {
                "type": "trade",
                "week": None,
                "amount": 52000,
                "date": "2025-03-10",
                "days_late": 0,
                "counterparty_nuban": "9034512987",
                "verified": True,
                "sender_id": "aminat-001",
                "receiver_id": "9034512987"
            },
        ]
    }

    result = score_member(aminat, model, explainer)

    print(f"\n=== AMINAT IBRAHIM ===")
    print(f"KOLA Score: {result['score']} / 850")
    print(f"Probability: {result['probability']:.3f}")
    print(f"\nSHAP Breakdown:")
    for factor, pts in sorted(result["shap"].items(), key=lambda x: abs(x[1]), reverse=True):
        print(f"  {pts:+d}  {factor}")
