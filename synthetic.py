"""
synthetic.py — generates 500 synthetic Ajo members for model training.

WHY SYNTHETIC DATA:
KOLA has no production history yet. Real credit bureaus train on years of
repayment outcomes. We generate data that precisely mirrors the four behavioural
archetypes we observe in Nigeria's informal savings groups. When real Squad
webhook data arrives, we retrain on that — the architecture stays identical.

THE FOUR ARCHETYPES (125 members each = 500 total):

  1. RELIABLE   — perfect or near-perfect record, often a collector
                  Label: creditworthy = 1

  2. INCONSISTENT — misses weeks, pays late, slow catchup
                  Label: creditworthy = 0

  3. GAMING     — suspiciously perfect: zero timing variance, circular flows
                  Label: creditworthy = 0 (flagged by anomaly detector)

  4. NEW MEMBER — only 3-6 weeks of history, promising but unproven
                  Label: None (excluded from supervised training)

Equal archetype sizes matter: a biased dataset (90% good, 10% bad) would
make the model say "always approve" and score well on accuracy — but that's
useless. Balanced classes force the model to actually learn the difference.
"""

import random
import uuid
import math
from datetime import datetime, timedelta
import json

random.seed(42)

NIGERIAN_FIRST_NAMES = [
    "Aminat", "Fatima", "Chioma", "Ngozi", "Blessing", "Halima",
    "Adaeze", "Kemi", "Aisha", "Zainab", "Nneka", "Folake",
    "Yetunde", "Shade", "Temi", "Amara", "Obiageli", "Hauwa",
    "Maryam", "Grace", "Comfort", "Patience", "Joy", "Faith",
    "Chinyere", "Ifeoma", "Nkechi", "Bunmi", "Sade", "Toyin",
    "Bimbo", "Dupe", "Ify", "Tola", "Remi", "Lara", "Yemi",
    "Funke", "Titi", "Bisi", "Mama", "Abike", "Modupe", "Seun"
]

NIGERIAN_LAST_NAMES = [
    "Ibrahim", "Okafor", "Abdullahi", "Eze", "Yusuf", "Nwosu",
    "Adeyemi", "Okonkwo", "Mohammed", "Chukwu", "Balogun", "Obi",
    "Musa", "Adeleke", "Abubakar", "Nwankwo", "Olawale", "Danjuma",
    "Suleiman", "Ogundele", "Afolabi", "Babatunde", "Nwofor", "Dike",
    "Aliyu", "Garba", "Usman", "Lawal", "Idowu", "Adekunle"
]

MARKETS = [
    "Mile 12 Friday Ajo", "Alaba Saturday Ajo", "Balogun Market Ajo",
    "Onitsha Monday Ajo", "Kano Central Ajo", "Wuse Market Ajo",
    "New Artisan Ajo", "Tejuosho Friday Ajo", "Idumota Ajo",
    "Computer Village Ajo", "Ladipo Market Ajo", "Oshodi Market Ajo"
]


def random_name() -> str:
    return f"{random.choice(NIGERIAN_FIRST_NAMES)} {random.choice(NIGERIAN_LAST_NAMES)}"


def random_nuban() -> str:
    return "90" + "".join(str(random.randint(0, 9)) for _ in range(8))


def generate_member(archetype: str = "reliable", group_id: str = None) -> dict:
    """
    Generate one Ajo member with a full 13-week contribution history.

    The `archetype` field drives every behavioural choice below.
    It mirrors the four real-world patterns we see in Nigerian Ajo groups.
    """
    member_id = str(uuid.uuid4())[:8]
    name = random_name()
    nuban = random_nuban()
    group = group_id or random.choice(MARKETS)
    total_weeks = 13
    start_date = datetime.now() - timedelta(weeks=total_weeks)
    week_amount = random.choice([2000, 3000, 5000, 5000, 5000, 10000])  # ₦5k most common

    events = []

    # ── ARCHETYPE 1: RELIABLE ──────────────────────────────────────────────────
    # Pays every week. At most one late payment (life happens).
    # 60% have been made group collector — highest social trust signal.
    # 50% have verified supplier/trade payments through Squad.
    if archetype == "reliable":
        late_week = random.randint(6, 12) if random.random() < 0.3 else None
        for week in range(1, total_weeks + 1):
            days_late = 0
            if week == late_week:
                days_late = random.randint(1, 2)
            amount = week_amount + random.randint(-200, 200)  # natural variation
            payment_date = start_date + timedelta(weeks=week - 1, days=days_late)
            events.append({
                "type": "contribution",
                "week": week,
                "amount": max(1000, amount),
                "date": payment_date.strftime("%Y-%m-%d"),
                "days_late": days_late,
                "verified": True,
                "sender_id": member_id,
                "receiver_id": f"collector-{group[:4]}"
            })
        # Supplier payments: half of reliable members have trade evidence
        if random.random() < 0.5:
            supplier_nuban = random_nuban()
            n_trades = random.randint(2, 5)
            for i in range(n_trades):
                trade_amount = random.randint(25000, 80000)
                trade_date = start_date + timedelta(weeks=i * 2 + 1, days=random.randint(0, 3))
                events.append({
                    "type": "trade",
                    "week": None,
                    "amount": trade_amount,
                    "date": trade_date.strftime("%Y-%m-%d"),
                    "days_late": 0,
                    "counterparty_nuban": supplier_nuban,
                    "verified": True,
                    "sender_id": member_id,
                    "receiver_id": supplier_nuban
                })
        collector_trust = 1 if random.random() < 0.6 else 0

    # ── ARCHETYPE 2: INCONSISTENT ──────────────────────────────────────────────
    # Misses 2-4 weeks. When late, often 3-6 days late.
    # Never made collector. No supplier payments.
    elif archetype == "inconsistent":
        n_misses = random.randint(2, 4)
        miss_weeks = set(random.sample(range(2, 12), n_misses))
        for week in range(1, total_weeks + 1):
            if week in miss_weeks:
                continue
            days_late = random.choices([0, 0, 1, 2, 3, 5, 6], weights=[3, 3, 1, 1, 1, 0.5, 0.5])[0]
            amount = week_amount + random.randint(-1000, 1000)  # more amount variation
            payment_date = start_date + timedelta(weeks=week - 1, days=days_late)
            events.append({
                "type": "contribution",
                "week": week,
                "amount": max(500, amount),
                "date": payment_date.strftime("%Y-%m-%d"),
                "days_late": days_late,
                "verified": True,
                "sender_id": member_id,
                "receiver_id": f"collector-{group[:4]}"
            })
        collector_trust = 0

    # ── ARCHETYPE 3: GAMING ────────────────────────────────────────────────────
    # Suspiciously perfect: every week, exact same amount, exact same day.
    # Real Ajo has natural variation. Zero variance = coordinated fraud.
    # These members also appear in each other's sender/receiver lists —
    # detectable by detect_wash_trading() in anomaly.py.
    elif archetype == "gaming":
        for week in range(1, total_weeks + 1):
            payment_date = start_date + timedelta(weeks=week - 1)  # no variation
            events.append({
                "type": "contribution",
                "week": week,
                "amount": week_amount,  # exact same every time
                "date": payment_date.strftime("%Y-%m-%d"),
                "days_late": 0,
                "verified": True,
                "sender_id": member_id,
                "receiver_id": f"circular-{group[:4]}"
            })
        collector_trust = 0

    # ── ARCHETYPE 4: NEW MEMBER ────────────────────────────────────────────────
    # Only 3-6 weeks of history. Pays on time — promising, but unproven.
    # Label is None: we exclude from training (insufficient evidence).
    # Score = provisional, shown with "Low confidence" badge in UI.
    elif archetype == "new":
        active_weeks = random.randint(3, 6)
        for week in range(1, active_weeks + 1):
            days_late = random.choices([0, 0, 0, 1], weights=[4, 4, 4, 1])[0]
            payment_date = start_date + timedelta(weeks=week - 1, days=days_late)
            events.append({
                "type": "contribution",
                "week": week,
                "amount": week_amount + random.randint(-300, 300),
                "date": payment_date.strftime("%Y-%m-%d"),
                "days_late": days_late,
                "verified": True,
                "sender_id": member_id,
                "receiver_id": f"collector-{group[:4]}"
            })
        collector_trust = 0

    else:
        events = []
        collector_trust = 0

    return {
        "member_id": member_id,
        "name": name,
        "nuban": nuban,
        "group": group,
        "archetype": archetype,
        "collector_trust": collector_trust,
        "events": events,
    }


def generate_gaming_group(size: int = 5) -> list[dict]:
    """
    Generate a circular wash-trading group.

    What happens: 5 members pay each other in a loop within the same week.
    A → B → C → D → E → A. All Squad-verified. All fraudulent.

    The detect_wash_trading() function in anomaly.py catches this by looking
    for members who are BOTH sender and receiver in the same week.
    This group generates those overlapping flows explicitly.
    """
    group_id = f"FAKE-{str(uuid.uuid4())[:4].upper()}"
    members = []
    for i in range(size):
        m = generate_member(archetype="gaming", group_id=group_id)
        members.append(m)

    # Plant circular payment references — each member sends to the next
    for i, member in enumerate(members):
        next_member = members[(i + 1) % size]
        for event in member["events"]:
            event["receiver_id"] = next_member["member_id"]
            # Also add a reverse flow to make the circle complete
            # (each member receives from the previous one)
            prev_member = members[(i - 1) % size]
            member["events"][0]["sender_id"] = prev_member["member_id"]

    return members


def generate_dataset(n_per_archetype: int = 125) -> list[dict]:
    """
    Generate 500 members: 125 per archetype.

    Args:
        n_per_archetype: members per archetype (default 125 → 500 total)

    Returns:
        list of member dicts ready for feature extraction and model training
    """
    dataset = []
    n_gaming_groups = n_per_archetype // 5  # groups of 5

    print(f"Generating {n_per_archetype} reliable members...")
    for _ in range(n_per_archetype):
        dataset.append(generate_member("reliable"))

    print(f"Generating {n_per_archetype} inconsistent members...")
    for _ in range(n_per_archetype):
        dataset.append(generate_member("inconsistent"))

    print(f"Generating {n_gaming_groups} circular groups ({n_per_archetype} gaming members)...")
    for _ in range(n_gaming_groups):
        group = generate_gaming_group(size=5)
        dataset.extend(group)

    print(f"Generating {n_per_archetype} new members...")
    for _ in range(n_per_archetype):
        dataset.append(generate_member("new"))

    reliable_count = sum(1 for m in dataset if m["archetype"] == "reliable")
    inconsistent_count = sum(1 for m in dataset if m["archetype"] == "inconsistent")
    gaming_count = sum(1 for m in dataset if m["archetype"] == "gaming")
    new_count = sum(1 for m in dataset if m["archetype"] == "new")

    print(f"\nDataset: {len(dataset)} total members")
    print(f"  Reliable (label=1):      {reliable_count}")
    print(f"  Inconsistent (label=0):  {inconsistent_count}")
    print(f"  Gaming (label=0):        {gaming_count}")
    print(f"  New (label=None):        {new_count}")

    return dataset


if __name__ == "__main__":
    dataset = generate_dataset()
    with open("data.json", "w") as f:
        json.dump(dataset, f, indent=2)
    print("\nSaved to data.json")
    print(f"Sample: {dataset[0]['name']} — archetype={dataset[0]['archetype']} — {len(dataset[0]['events'])} events")
