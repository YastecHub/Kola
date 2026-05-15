"""
features.py — translates raw Ajo events into the five numbers KOLA scores on.

WHY EXACTLY FIVE FEATURES:
XGBoost works best when every feature earns its place. Ten features on a
200-person dataset causes overfitting — the model memorises noise instead of
learning real credit behaviour. Five features, each answering a distinct
question, gives the model a clean signal.

The five questions:
  1. Does she show up?          → contribution_streak
  2. When late, how fast?       → catchup_speed_days
  3. Is her amount consistent?  → amount_std
  4. Does the group trust her?  → collector_trust
  5. Does real trade back her?  → trade_regularity

RETROACTIVE HISTORY IMPORT:
Events carry a `source` field that tells us how trustworthy they are:
  - "squad_verified"  : cryptographically signed Squad webhook (weight 1.0)
  - "admin_attested"  : group admin testified this payment happened  (weight 0.75)
  - "self_reported"   : member self-declared, unverified              (weight 0.40)

We scale features proportionally by the weighted sum of events.
This means a member with 10 admin-attested weeks gets credit for 7.5
equivalent squad-verified weeks — better than zero, honest about provenance.
"""

import math

# Source trust weights — how much we believe each data source
SOURCE_WEIGHTS = {
    "squad_verified": 1.00,
    "admin_attested": 0.75,
    "self_reported":  0.40,
}

FEATURE_NAMES = [
    "contribution_streak",
    "catchup_speed_days",
    "amount_std",
    "collector_trust",
    "trade_regularity",
]

# Short names used in the API SHAP output — match exactly to data.ts
SHAP_KEYS = ["streak", "catchup", "amount_std", "collector", "trade"]

# Map FEATURE_NAMES → SHAP_KEYS (same order)
FEATURE_TO_SHAP = dict(zip(FEATURE_NAMES, SHAP_KEYS))


def _event_weight(event: dict) -> float:
    """Returns the trust weight for an event based on its source."""
    source = event.get("source", "squad_verified")
    return SOURCE_WEIGHTS.get(source, 1.0)


def extract_features(member: dict) -> dict:
    """
    Turns one member's event history into a flat feature dict.

    Events carry an optional `source` field (default: "squad_verified"):
      - "squad_verified"  : Squad webhook — full trust
      - "admin_attested"  : group admin vouched for this — 75% trust
      - "self_reported"   : member declared — 40% trust

    Features are weighted by source trust so retroactive history from
    admin attestation contributes meaningfully without overstating confidence.
    """
    events = member.get("events", [])
    contributions = [e for e in events if e.get("type") == "contribution"]
    trade_events = [e for e in events if e.get("type") in ("trade", "supplier_payment")]

    total_window = 13

    # ── 1. CONTRIBUTION STREAK ─────────────────────────────────────────────────
    # Weighted streak: admin-attested weeks count as 0.75 of a real week.
    # We build a week → weight map and count backward from most recent.
    week_weight: dict[int, float] = {}
    for e in contributions:
        w = e.get("week")
        if w is not None:
            # Take the max weight if a week has multiple events
            week_weight[w] = max(week_weight.get(w, 0), _event_weight(e))

    streak = 0.0
    for week in range(total_window, 0, -1):
        if week in week_weight:
            streak += week_weight[week]
        else:
            break
    streak = round(streak, 2)

    # ── 2. CATCHUP SPEED (days) ────────────────────────────────────────────────
    # Weighted average days late: admin-attested late payments count at 75%.
    late_payments = [e for e in contributions if e.get("days_late", 0) > 0]
    if late_payments:
        total_weight = sum(_event_weight(e) for e in late_payments)
        weighted_late = sum(e["days_late"] * _event_weight(e) for e in late_payments)
        catchup_speed_days = weighted_late / total_weight if total_weight > 0 else 0.0
    else:
        catchup_speed_days = 0.0

    # ── 3. AMOUNT STANDARD DEVIATION ──────────────────────────────────────────
    # Only use squad_verified amounts for std — admin-attested amounts are
    # often round numbers entered by the admin and don't reflect real variance.
    verified_amounts = [
        e["amount"] for e in contributions
        if e.get("source", "squad_verified") == "squad_verified"
    ]
    if len(verified_amounts) > 1:
        mean = sum(verified_amounts) / len(verified_amounts)
        amount_std = math.sqrt(sum((a - mean) ** 2 for a in verified_amounts) / len(verified_amounts))
    elif contributions:
        # Fall back to all events if no verified amounts yet
        amounts = [e["amount"] for e in contributions]
        if len(amounts) > 1:
            mean = sum(amounts) / len(amounts)
            amount_std = math.sqrt(sum((a - mean) ** 2 for a in amounts) / len(amounts))
        else:
            amount_std = 0.0
    else:
        amount_std = 0.0

    # ── 4. COLLECTOR TRUST ─────────────────────────────────────────────────────
    # Binary from squad VA admin grant OR admin attestation.
    # Attested collector trust is weighted 0.75 (still meaningful — if Mama Bisi
    # says Aminat was her collector for 3 months, that's strong social proof).
    raw_collector = member.get("collector_trust", 0)
    collector_source = member.get("collector_trust_source", "squad_verified")
    collector_trust = round(float(bool(raw_collector)) * SOURCE_WEIGHTS.get(collector_source, 1.0), 2)

    # ── 5. TRADE REGULARITY ────────────────────────────────────────────────────
    # Sum of weights across trade events. Squad-verified supplier payment = 1.0.
    # Admin-attested trade = 0.75. Both count toward demonstrating economic activity.
    trade_regularity = round(sum(_event_weight(e) for e in trade_events), 2)

    return {
        "contribution_streak": streak,
        "catchup_speed_days": round(catchup_speed_days, 2),
        "amount_std": round(amount_std, 2),
        "collector_trust": collector_trust,
        "trade_regularity": trade_regularity,
    }


def assign_label(member: dict) -> int | None:
    """
    Returns the training label for this member.

    XGBClassifier needs binary labels:
      1 = creditworthy (lender should approve)
      0 = not creditworthy (lender should decline or scrutinise)
      None = exclude from training (insufficient history)

    We know the truth for synthetic members via their archetype.
    For real members, we would derive this from actual loan outcomes.
    """
    archetype = member.get("archetype", "reliable")

    if archetype == "reliable":
        return 1
    elif archetype in ("inconsistent", "gaming"):
        return 0
    elif archetype == "new":
        return None  # excluded from training — not enough data to label
    else:
        return 0
