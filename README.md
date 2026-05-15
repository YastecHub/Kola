<<<<<<< HEAD
## KOLA

Nigeria's informal credit bureau for Ajo groups.

Backend implementation lives in [kola_backend](./kola_backend).

## Team

- Product / Pitch - Peculiar
- Backend / Squad Integration - Yasir
- AI / ML - David
- Frontend / Demo - Progress
=======
# KOLA — Credit Bureau for Nigeria's Ajo Economy

KOLA is a credit scoring infrastructure built on Squad's payment rails. It converts Ajo group contribution history — verified through Squad Virtual Accounts and HMAC-signed webhooks — into portable credit identities for Nigeria's 14 million informal savers.

A microfinance bank queries KOLA's API, pays ₦500, and gets a 300–850 credit score with a full AI-generated explanation in under 60 seconds. No salary slips. No bank statements. Just two years of showing up.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        KOLA Platform                            │
│                                                                 │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────┐  │
│  │  kola_front  │    │ kola_backend │    │    kola_ai       │  │
│  │  (Next.js)   │───▶│  (FastAPI)   │───▶│  (FastAPI +      │  │
│  │  Vercel      │    │  Render      │    │   XGBoost)       │  │
│  └──────────────┘    └──────┬───────┘    │  Railway         │  │
│                             │            └──────────────────┘  │
└─────────────────────────────┼───────────────────────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │    Squad APIs      │
                    │  Virtual Accounts  │
                    │  Webhooks (HMAC)   │
                    │  Tx Verification   │
                    └───────────────────┘
                              │
                    ┌─────────▼─────────┐
                    │  Supabase Postgres │
                    │  Groups, Members   │
                    │  Economic Events   │
                    │  Score History     │
                    └───────────────────┘
```

**Data flow:**
1. Admin registers an Ajo group → backend creates Squad Virtual Accounts for every member (real NUBANs)
2. Member makes a contribution → Squad fires a signed webhook to `POST /api/webhooks/squad`
3. Backend verifies HMAC-SHA512 signature, double-verifies via Squad transaction API, stores as `EconomicEvent(verified=True)`
4. Lender queries `GET /api/scores/{member_id}` → backend calls the AI service with the event history → XGBoost returns score + SHAP explanation
5. Lender sees: score 714, breakdown by streak/recovery/consistency/trust/trade, anomaly flag

---

## Services

| Service | Stack | Host | Purpose |
|---|---|---|---|
| `kola_frontend` | Next.js 14, Tailwind, TypeScript | Vercel | Lender dashboard, group admin UI |
| `kola_backend` | FastAPI, SQLAlchemy, Supabase | Render | Squad integration, data layer, score API |
| `kola_ai` | FastAPI, XGBoost, SHAP | Railway | Credit scoring model and explainability |

---

## Squad API Integration

KOLA uses three Squad API surfaces. All are load-bearing — removing any one breaks the system.

### 1. Virtual Account Creation
Called when a group is registered. Every member gets a dedicated NUBAN.

```
POST https://api-d.squadco.com/virtual-account
Authorization: Bearer <SQUAD_SECRET_KEY>
```

The account number is stored as `GroupMember.squad_va_number`. All contributions flow through this account, creating the audit trail that becomes the credit score.

### 2. Webhook Ingestion
Squad calls `POST /api/webhooks/squad` on every payment event. The backend:
- Reads the raw request body before JSON parsing
- Computes `HMAC-SHA512(SQUAD_SECRET_KEY, raw_body)`
- Rejects any request where the signature doesn't match `X-Squad-Signature`
- Calls Squad's transaction verification endpoint to double-confirm
- Stores the event with `verified=True` and the signature on record

No fabricated event can pass HMAC verification. This is what makes KOLA scores auditable.

### 3. Transaction Verification
For every webhook, the backend independently verifies the transaction reference with Squad before storing. A payment isn't evidence until Squad confirms it twice.

---

## AI Scoring System (`kola_ai`)

### Model
**XGBClassifier** trained on 500 synthetic Ajo members across four archetypes: reliable, inconsistent, gaming, and new.

Why XGBoost over a neural network: the dataset is tabular and small. Neural networks need thousands of labelled examples to generalise. XGBoost handles missing features natively (a member with no trade events doesn't crash the model) and produces mathematically exact SHAP explanations.

### Features
Five features. Each answers one question about financial character.

| Feature | Question | Signal |
|---|---|---|
| `contribution_streak` | Does she show up? | Weighted weeks of consecutive contributions |
| `catchup_speed_days` | When late, how fast does she recover? | Weighted average days overdue |
| `amount_std` | Is she consistent or erratic? | Standard deviation of contribution amounts |
| `collector_trust` | Does her group trust her with their money? | Whether she has served as group collector |
| `trade_regularity` | Does real commerce flow through her account? | Weighted count of trade/supplier payment events |

### Score Formula
```
KOLA Score = int(300 + (probability × 550))
```
- `probability` is the XGBClassifier's confidence that this member is creditworthy (0.0–1.0)
- 300 = floor (FICO-aligned minimum)
- 850 = ceiling (FICO-aligned maximum)
- Aminat week 4: probability 0.345 → score **490**
- Aminat week 13: probability 0.753 → score **714**

### Explainability (SHAP)
Every score ships with a SHAP breakdown. TreeExplainer gives exact Shapley values — not approximations. The lender sees exactly how much each feature contributed to the final number.

```json
{
  "score": 714,
  "shap": {
    "streak": 89,
    "catchup": 41,
    "amount_std": 52,
    "collector": 35,
    "trade": 17
  },
  "confidence": "High",
  "anomaly_flag": false
}
```

### Anomaly Detection
Isolation Forest runs in parallel with XGBoost. It flags members whose payment patterns are statistical outliers — too-perfect contributions, circular payment graphs, sudden trade spikes with no prior history. A flagged score is still returned; the lender makes the final call.

### Data Trust Weights
Not all events are equal. The model weights by source:

| Source | Weight |
|---|---|
| `squad_verified` (HMAC webhook) | 1.00 |
| `admin_attested` (group admin vouch) | 0.75 |
| `self_reported` (member declared) | 0.40 |

Groups without Squad can receive provisional scores. When they join Squad, their event weights upgrade from 0.75 to 1.00 automatically.

---

## Local Development

### Prerequisites
- Python 3.11+
- Node.js 20+
- A Supabase project
- Squad sandbox credentials

### Backend (`kola_backend`)

```bash
cd kola_backend
cp .env.example .env
# fill in SUPABASE_DATABASE_URL, SQUAD_SECRET_KEY, SQUAD_PUBLIC_KEY, API_KEY
pip install -r requirements.txt
alembic upgrade head
uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

Set `SQUAD_MOCK_MODE=true` to skip real Squad calls during development. Mock mode generates fake NUBANs locally.

Interactive docs: `http://localhost:8001/docs`

### AI Service (`kola_ai`)

```bash
cd kola_ai
cp .env.example .env
# set KOLA_API_KEY (default: kola-dev-key-2025 in dev)
pip install -r requirements.txt
python model.py        # trains and saves kola_model.pkl + kola_explainer.pkl
uvicorn api:app --host 0.0.0.0 --port 8000 --reload
```

The model trains in under 10 seconds on a laptop. After `model.py` runs, `kola_model.pkl` and `kola_explainer.pkl` appear in the directory. The API will not start without them.

Health check: `GET http://localhost:8000/health`

### Frontend (`kola_frontend`)

```bash
cd kola_frontend
cp .env.example .env.local
# set NEXT_PUBLIC_API_URL=http://localhost:8001
npm install
npm run dev
```

App runs at `http://localhost:3000`

---

## Environment Variables

### `kola_backend`

| Variable | Required | Description |
|---|---|---|
| `SUPABASE_DATABASE_URL` | Yes | `postgresql+psycopg://...` connection string |
| `SQUAD_SECRET_KEY` | Yes | Squad secret key (Bearer token for API calls) |
| `SQUAD_PUBLIC_KEY` | Yes | Squad public key |
| `SQUAD_BASE_URL` | Yes | `https://sandbox-api-d.squadco.com` (sandbox) or `https://api-d.squadco.com` (prod) |
| `SQUAD_MOCK_MODE` | No | `true` to skip real Squad calls. Default: `false` |
| `SQUAD_BENEFICIARY_ACCOUNT` | Yes (prod) | Account number that receives settled funds |
| `WEBHOOK_SECRET` | No | Overrides `SQUAD_SECRET_KEY` for webhook HMAC verification |
| `API_KEY` | Yes | Internal API key for frontend → backend calls |
| `BACKEND_CORS_ORIGINS` | Yes | Comma-separated allowed origins |
| `KOLA_AI_URL` | No | Railway URL for AI service. Falls back to formula scoring if unset |
| `KOLA_AI_KEY` | No | API key for AI service. Default: `kola-dev-key-2025` |

### `kola_ai`

| Variable | Required | Description |
|---|---|---|
| `KOLA_API_KEY` | No | Auth key for `/score` endpoint. Default: `kola-dev-key-2025` |
| `PORT` | No | Port to listen on. Default: `8000` |

### `kola_frontend`

| Variable | Required | Description |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | Yes | Backend base URL |

---

## Deployment

### Backend → Render
Configured via `render.yaml`. Set the `sync: false` env vars manually in the Render dashboard after first deploy.

```bash
# Render picks this up automatically from render.yaml on push to main
git push team main
```

### AI Service → Railway
```bash
cd kola_ai
python model.py    # generate model files first
# commit kola_model.pkl and kola_explainer.pkl
# Railway deploys on git push — uses Procfile
```

**Important:** The model files (`kola_model.pkl`, `kola_explainer.pkl`) must be committed to the repo or generated during the Railway build step. The API will not start without them. Set `KOLA_API_KEY` in Railway environment variables.

After deploying, set `KOLA_AI_URL` and `KOLA_AI_KEY` in Render's environment variables so the backend can reach the AI service.

### Frontend → Vercel
Configured via `kola_frontend/vercel.json`. Set `NEXT_PUBLIC_API_URL` to the Render backend URL in Vercel environment settings.

---

## API Reference

Full interactive docs available at `/docs` on both backend and AI service.

### Backend

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Service health |
| `POST` | `/api/groups/` | X-API-Key | Create Ajo group + Squad Virtual Accounts |
| `POST` | `/api/webhooks/squad` | HMAC signature | Ingest Squad payment webhook |
| `GET` | `/api/scores/{member_id}` | X-API-Key | Get credit score by member UUID |
| `GET` | `/api/scores/trader/{phone_or_id}` | X-API-Key | Get credit score by phone or member ID |

### AI Service

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Model load status |
| `POST` | `/score` | X-Api-Key | Score one member |
| `POST` | `/score/batch` | X-Api-Key | Score multiple members |

---

## Repository Structure

```
kola/
├── kola_frontend/          # Next.js lender dashboard and group admin UI
│   ├── app/                # App Router pages
│   ├── components/         # KolaScreens and UI components
│   └── lib/                # API client and data utilities
│
├── kola_backend/           # FastAPI backend, Squad integration, data layer
│   ├── app/
│   │   ├── api/            # Route handlers (groups, scores, webhooks)
│   │   ├── core/           # Config, security, settings
│   │   ├── models/         # SQLAlchemy ORM models
│   │   ├── schemas/        # Pydantic request/response schemas
│   │   └── services/       # Squad client, event storage, score builder
│   ├── alembic/            # Database migrations
│   └── API_CONTRACT.md     # Full API contract with examples
│
├── kola_ai/                # XGBoost scoring model and explainability API
│   ├── api.py              # FastAPI app — POST /score endpoint
│   ├── model.py            # Training pipeline
│   ├── features.py         # Feature engineering (5 features)
│   ├── anomaly.py          # Isolation Forest anomaly detection
│   ├── synthetic.py        # Synthetic training data generation
│   ├── Procfile            # Railway startup command
│   └── requirements.txt    # Python dependencies
│
└── render.yaml             # Render deployment config for backend
```

---

## The Problem We're Solving

Nigeria's formal credit bureaus cover 8% of the adult population. South Africa's cover 64%. The gap isn't data — it's data infrastructure. 14 million Nigerians contribute to Ajo groups every week, building payment histories that prove creditworthiness. None of it touches a credit bureau.

KOLA makes Squad the data layer. Every HMAC-signed contribution webhook is a credit event. Thirteen weeks of showing up is a credit identity.

The comparable: Esusu (US, diaspora Ajo groups) — $1.2B valuation.
The market: Nigeria, where the problem is 10x larger and 0% served.

---

## Team

Built by Team KOLA for GTCO SquadCo Hackathon 3.0 — Challenge 02: Smart Systems, The Intelligent Economy.
>>>>>>> 37105b7fa119671e2cc4326c4a3e2c81a3137fbf
