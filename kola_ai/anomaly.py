"""
anomaly.py — two-layer fraud detection for KOLA.

LAYER 1 — WASH TRADING DETECTOR (rule-based, deterministic):
  Catches circular payment fraud where 5 friends pay each other in a loop.
  Algorithm: within any single week, flag if 3+ members appear as BOTH
  sender AND receiver. Exact attack pattern, exact detection.
  Source: PRD spec, Section 4.3.

LAYER 2 — ISOLATION FOREST (ML, unsupervised):
  Learns what a normal credit profile looks like across all 5 features.
  Flags anyone whose feature vector sits far from the normal cluster.
  Catches novel attack patterns we didn't anticipate in the rules.

WHY TWO LAYERS:
  Rule-based: zero false negatives on known attacks (wash trading).
  ML-based: generalises to unknown attacks (new fraud patterns).
  Neither alone is sufficient — the combination covers both.

OUTPUT ALWAYS GOES THROUGH HUMAN REVIEW, NEVER AUTO-REJECTION:
  Flagged members get a REVIEW REQUIRED status.
  A human at the lender makes the final call.
  This prevents the model from being a denial machine for legitimate edge cases.
"""

import numpy as np
from sklearn.ensemble import IsolationForest
from features import extract_features, FEATURE_NAMES


# ── LAYER 1: WASH TRADING DETECTION ──────────────────────────────────────────


def group_events_by_week(group_events: list) -> dict:
    """
    Groups a flat list of payment events by their week number.

    Each event must have:
      - week: int
      - sender_id: str
      - receiver_id: str

    Returns { week_number: [events_this_week] }
    """
    by_week = {}
    for event in group_events:
        week = event.get("week")
        if week is None:
            continue
        if week not in by_week:
            by_week[week] = []
        by_week[week].append(event)
    return by_week


def detect_wash_trading(group_events: list) -> tuple[bool, str | None]:
    """
    Detects circular wash-trading within an Ajo group.

    THE ATTACK: 5 friends form a fake group and pay each other in a circle
    every week. A → B → C → D → E → A. All Squad-verified. All fraudulent.

    THE DETECTION: In any given week, a legitimate member is either paying
    the group (sender) or holding the pot (receiver). They cannot be both
    unless they are routing money through the system artificially.

    If 3+ members appear as BOTH sender AND receiver in the same week,
    the group is flagged for circular payment fraud.

    Args:
        group_events: flat list of all payment events across all group members.
                      Each event needs: week, sender_id, receiver_id.

    Returns:
        (is_flagged: bool, reason: str | None)
    """
    weekly_flows = group_events_by_week(group_events)

    for week, flows in weekly_flows.items():
        senders = {f["sender_id"] for f in flows if f.get("sender_id")}
        receivers = {f["receiver_id"] for f in flows if f.get("receiver_id")}
        overlap = senders & receivers

        if len(overlap) > 2:
            return (
                True,
                f"Circular pattern: {len(overlap)} members both sending and receiving same week"
            )

    return False, None


# ── LAYER 2: ISOLATION FOREST ─────────────────────────────────────────────────


def build_isolation_forest(dataset: list) -> IsolationForest:
    """
    Train an Isolation Forest on the full synthetic dataset.

    HOW ISOLATION FOREST WORKS:
    It randomly partitions the feature space with decision trees. An outlier
    (anomaly) sits alone in feature space and gets isolated quickly — it takes
    fewer cuts to separate it. A normal member sits in a dense cluster and
    requires many cuts to isolate.

    anomaly_score closer to -1.0 = more anomalous.
    anomaly_score closer to 0.0 = more normal.

    We set contamination=0.05 because we estimate ~5% of all Ajo members
    may have some form of suspicious pattern (generous estimate; real fraud
    is rarer but we'd rather review legitimate members than miss fraud).
    """
    X = []
    for member in dataset:
        features = extract_features(member)
        X.append([features[f] for f in FEATURE_NAMES])

    forest = IsolationForest(
        n_estimators=100,
        contamination=0.05,
        random_state=42
    )
    forest.fit(np.array(X))
    return forest


def score_member_anomaly(member: dict, forest: IsolationForest) -> dict:
    """
    Run both anomaly layers on a single member.

    Returns:
      {
        "is_flagged": bool,
        "reason": str | None,
        "isolation_score": float  # -1.0 to 0.0, for transparency
      }
    """
    features = extract_features(member)
    X = np.array([[features[f] for f in FEATURE_NAMES]])

    iso_prediction = forest.predict(X)[0]   # -1 = anomaly, 1 = normal
    iso_score = float(forest.score_samples(X)[0])

    is_flagged = iso_prediction == -1
    reason = None

    if is_flagged:
        # Determine which features are most responsible
        if features["contribution_streak"] == 13 and features["catchup_speed_days"] == 0.0 and features["amount_std"] == 0.0:
            reason = "Perfect payment record with zero variation — consistent with coordinated fraud"
        else:
            reason = "Unusual pattern across multiple features — does not match any known normal profile"

    return {
        "is_flagged": is_flagged,
        "reason": reason,
        "isolation_score": round(iso_score, 4),
    }


def screen_group(group_members: list, forest: IsolationForest) -> dict:
    """
    Full group-level screening: wash trading detection + per-member anomaly.

    Called when a new Ajo group registers. If the group is clean, Squad VA
    provisioning proceeds. If flagged, it goes to manual review.
    """
    # Collect all events from all members for wash trading check
    all_events = []
    for member in group_members:
        all_events.extend(member.get("events", []))

    wash_flagged, wash_reason = detect_wash_trading(all_events)

    # Per-member Isolation Forest check
    member_results = [score_member_anomaly(m, forest) for m in group_members]
    flagged_count = sum(1 for r in member_results if r["is_flagged"])
    flag_rate = flagged_count / len(group_members) if group_members else 0

    # Group verdict
    reasons = []
    if wash_flagged:
        reasons.append(wash_reason)
    if flag_rate >= 0.6:
        reasons.append(f"{flagged_count}/{len(group_members)} members show anomalous patterns")
    if len(group_members) < 8:
        reasons.append(f"Group has only {len(group_members)} members — typical Ajo groups have 15-20")

    is_group_flagged = wash_flagged or flag_rate >= 0.6

    return {
        "group_name": group_members[0].get("group", "Unknown") if group_members else "Unknown",
        "member_count": len(group_members),
        "flagged_count": flagged_count,
        "wash_trading_detected": wash_flagged,
        "is_flagged": is_group_flagged,
        "reasons": reasons,
        "members": member_results,
    }


if __name__ == "__main__":
    from synthetic import generate_dataset, generate_gaming_group

    print("Training anomaly detector on 500-member dataset...")
    dataset = generate_dataset()
    forest = build_isolation_forest(dataset)

    print("\n=== Reliable member ===")
    reliable = next(m for m in dataset if m["archetype"] == "reliable")
    result = score_member_anomaly(reliable, forest)
    print(f"  {reliable['name']}: flagged={result['is_flagged']} score={result['isolation_score']}")

    print("\n=== Gaming group (wash trading) ===")
    fake_group = generate_gaming_group(size=5)
    all_events = []
    for m in fake_group:
        all_events.extend(m.get("events", []))

    wash_flag, wash_reason = detect_wash_trading(all_events)
    print(f"  Wash trading detected: {wash_flag}")
    if wash_reason:
        print(f"  Reason: {wash_reason}")

    group_result = screen_group(fake_group, forest)
    print(f"  Group flagged: {group_result['is_flagged']}")
    print(f"  All reasons: {group_result['reasons']}")
