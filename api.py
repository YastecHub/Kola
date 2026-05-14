"""
api.py — KOLA Credit Bureau API.

SINGLE ENDPOINT: POST /score

Takes a member's Squad-verified event history.
Returns a KOLA Score, probability, SHAP breakdown, and anomaly flag.
Response SLA: < 2 seconds (model inference is ~5ms; network is the bottleneck).

AUTHENTICATION:
  X-Api-Key header. In production this is HMAC-SHA512 (same as Squad webhooks).
  Dev key: kola-dev-key-2025

CORS:
  Allows localhost:3000 (Progress's frontend) and kola.vercel.app (production).

HOW IT INTEGRATES WITH THE FRONTEND:
  1. Lender queries POST /score with Aminat's member_id and events
  2. API returns score=714, probability=0.753, shap={...}
  3. Progress's dashboard renders the SHAP bars from the live API response
  4. Currently the frontend uses hardcoded data from lib/data.ts;
     wiring to this API is Progress's next task
"""

import os
import pickle
import sys
import numpy as np
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
import uvicorn

# ── Startup: load models ──────────────────────────────────────────────────────

model = None
explainer = None
forest = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    global model, explainer, forest

    # Load scoring model
    try:
        with open("kola_model.pkl", "rb") as f:
            model = pickle.load(f)
        with open("kola_explainer.pkl", "rb") as f:
            explainer = pickle.load(f)
        print("Scoring model loaded.")
    except FileNotFoundError:
        print("No trained model found. Run: python model.py")
        print("API will start but /score will return 503 until model is trained.")

    # Train anomaly detector on synthetic data
    # In production: retrain nightly on real Squad webhook events
    try:
        from anomaly import build_isolation_forest
        from synthetic import generate_dataset
        dataset = generate_dataset()
        forest = build_isolation_forest(dataset)
        print("Anomaly detector ready.")
    except Exception as e:
        print(f"Anomaly detector failed to load: {e}")

    yield  # app runs here

    print("KOLA API shutting down.")


app = FastAPI(
    title="KOLA Credit Bureau API",
    description="Squad-verified informal credit scoring for Nigeria's 14M Ajo participants",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "https://kola.vercel.app",
        "https://*.vercel.app",
    ],
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)


# ── Request / Response models ─────────────────────────────────────────────────

class ContributionEvent(BaseModel):
    """A weekly Ajo contribution — Squad-verified, admin-attested, or self-reported."""
    type: str                              # "contribution"
    week: Optional[int] = None
    amount: int                            # NGN
    date: str                              # "YYYY-MM-DD"
    days_late: int = 0
    verified: bool = True
    source: str = "squad_verified"         # "squad_verified" | "admin_attested" | "self_reported"
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None


class TradeEvent(BaseModel):
    """A supplier or market payment — Squad-verified or admin-attested."""
    type: str = "trade"                    # "trade" or "supplier_payment"
    amount: int                            # NGN
    date: str                              # "YYYY-MM-DD"
    counterparty_nuban: Optional[str] = None
    verified: bool = True
    source: str = "squad_verified"
    sender_id: Optional[str] = None
    receiver_id: Optional[str] = None


class ScoreRequest(BaseModel):
    """
    POST /score request body.

    For retroactive history import, send historical events with
    source="admin_attested". These contribute to the score at 75% weight
    versus Squad-verified events.
    """
    member_id: str
    events: list[ContributionEvent]
    trade_events: list[TradeEvent] = []
    collector_trust: int = 0
    collector_trust_source: str = "squad_verified"  # source of collector status


class ShapBreakdown(BaseModel):
    streak: int
    catchup: int
    amount_std: int
    collector: int
    trade: int


class ScoreResponse(BaseModel):
    """
    POST /score response — PRD contract plus confidence and history provenance.
    """
    score: int                             # 300-850 KOLA Score
    probability: float                     # 0.0-1.0 model confidence
    shap: ShapBreakdown                    # factor contributions in score points
    anomaly_flag: bool                     # True = flagged for review
    anomaly_reason: Optional[str]          # plain English reason if flagged
    weeks_of_history: int                  # total distinct weeks with any payment
    weeks_squad_verified: int              # weeks backed by Squad webhooks
    weeks_admin_attested: int              # weeks backed by group admin attestation
    confidence: str                        # "High" | "Medium" | "Low — provisional"
    confidence_detail: str                 # human-readable provenance summary


# ── Auth ──────────────────────────────────────────────────────────────────────

KOLA_API_KEY = os.environ.get("KOLA_API_KEY", "kola-dev-key-2025")


def verify_key(x_api_key: str = Header(...)) -> str:
    if x_api_key != KOLA_API_KEY:
        raise HTTPException(status_code=401, detail="Invalid API key")
    return x_api_key


# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/")
def root():
    return {
        "service": "KOLA Credit Bureau API",
        "status": "live",
        "version": "1.0.0",
        "endpoint": "POST /score",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "model_loaded": model is not None,
        "anomaly_detector_loaded": forest is not None,
        "status": "ready" if (model and forest) else "degraded",
    }


@app.post("/score", response_model=ScoreResponse)
def score(request: ScoreRequest, x_api_key: str = Header(...)):
    """
    Score one Ajo member.

    Called by the lender dashboard when they click "Query Credit Score."
    Response time: < 2 seconds (model inference ~5ms, anomaly check ~10ms).

    The SHAP breakdown tells the lender exactly what drove the score:
    - Positive numbers = features that helped (streak, trade activity)
    - Negative numbers = features that hurt (amount inconsistency)

    If anomaly_flag is True, the lender should review before approving.
    The score is still returned — the lender makes the final call.
    """
    verify_key(x_api_key)

    if not model or not explainer:
        raise HTTPException(
            status_code=503,
            detail="Scoring model not loaded. Run: python model.py"
        )

    # Build the member dict that features.py and model.py expect
    member = {
        "member_id": request.member_id,
        "collector_trust": request.collector_trust,
        "collector_trust_source": request.collector_trust_source,
        "events": [
            {
                "type": e.type,
                "week": e.week,
                "amount": e.amount,
                "date": e.date,
                "days_late": e.days_late,
                "verified": e.verified,
                "source": e.source,
                "sender_id": e.sender_id or request.member_id,
                "receiver_id": e.receiver_id or "collector",
            }
            for e in request.events
        ] + [
            {
                "type": t.type,
                "week": None,
                "amount": t.amount,
                "date": t.date,
                "days_late": 0,
                "counterparty_nuban": t.counterparty_nuban,
                "verified": t.verified,
                "source": t.source,
                "sender_id": t.sender_id or request.member_id,
                "receiver_id": t.receiver_id or t.counterparty_nuban or "unknown",
            }
            for t in request.trade_events
        ]
    }

    # Score
    from model import score_member
    result = score_member(member, model, explainer)

    # Anomaly check — two-layer approach
    anomaly_flag = False
    anomaly_reason = None

    if forest:
        from anomaly import score_member_anomaly, detect_wash_trading

        # Layer 1: Wash trading — always run. Deterministic. Catches the exact fraud pattern.
        wash_flag, wash_reason = detect_wash_trading(member["events"])
        if wash_flag:
            anomaly_flag = True
            anomaly_reason = wash_reason
        else:
            # Layer 2: Isolation Forest — only for ambiguous scores.
            # A member scoring 600+ is very unlikely to be gaming.
            # Applying IF to high-scoring members produces false positives on
            # legitimate members whose features sit at the edge of the training distribution.
            if result["score"] < 600:
                anomaly = score_member_anomaly(member, forest)
                if anomaly["is_flagged"]:
                    anomaly_flag = True
                    anomaly_reason = anomaly["reason"]

    # History provenance — count weeks by source
    contrib_events = [e for e in request.events if e.week is not None]
    squad_weeks = {e.week for e in contrib_events if e.source == "squad_verified"}
    attested_weeks = {e.week for e in contrib_events if e.source == "admin_attested"}
    all_weeks = {e.week for e in contrib_events}

    weeks_of_history = len(all_weeks)
    weeks_squad_verified = len(squad_weeks)
    weeks_admin_attested = len(attested_weeks - squad_weeks)  # attested-only weeks

    # Confidence is based on squad-verified weeks (attested history helps score but not confidence tier)
    if weeks_squad_verified >= 12:
        confidence = "High"
        confidence_detail = f"{weeks_squad_verified} weeks Squad-verified"
    elif weeks_squad_verified >= 6:
        confidence = "Medium"
        if weeks_admin_attested > 0:
            confidence_detail = f"{weeks_squad_verified} weeks Squad-verified + {weeks_admin_attested} admin-attested"
        else:
            confidence_detail = f"{weeks_squad_verified} weeks Squad-verified"
    elif weeks_admin_attested >= 8:
        confidence = "Medium"
        confidence_detail = f"{weeks_admin_attested} weeks admin-attested (retroactive import)"
    else:
        confidence = "Low — provisional"
        if weeks_admin_attested > 0:
            confidence_detail = f"{weeks_squad_verified} weeks Squad-verified, {weeks_admin_attested} admin-attested — building history"
        else:
            confidence_detail = f"{weeks_squad_verified} weeks verified — building history"

    return ScoreResponse(
        score=result["score"],
        probability=result["probability"],
        shap=ShapBreakdown(**result["shap"]),
        anomaly_flag=anomaly_flag,
        anomaly_reason=anomaly_reason,
        weeks_of_history=weeks_of_history,
        weeks_squad_verified=weeks_squad_verified,
        weeks_admin_attested=weeks_admin_attested,
        confidence=confidence,
        confidence_detail=confidence_detail,
    )


@app.post("/score/batch")
def score_batch(requests: list[ScoreRequest], x_api_key: str = Header(...)):
    """
    Score multiple members at once.
    Used by MFB partners screening their Ajo portfolios.
    Returns results in the same order as input.
    """
    verify_key(x_api_key)
    if not model or not explainer:
        raise HTTPException(status_code=503, detail="Scoring model not loaded.")

    results = []
    for req in requests:
        single_result = score(req, x_api_key)
        results.append(single_result)

    return {"count": len(results), "results": results}


if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=False)
