# KOLA Backend

FastAPI backend for KOLA, Nigeria's informal credit bureau for Ajo groups. Squad is treated as the source of truth for verified contribution and payment events.

## Implemented

- Async FastAPI app with SQLAlchemy 2.0 and Alembic.
- Supabase PostgreSQL configuration through `pydantic-settings`.
- Squad virtual account creation flow for group members.
- Squad webhook ingestion with HMAC-SHA512 verification for full-body and virtual-account v2/v3 signatures.
- Immutable economic event storage with raw payload and signature.
- Internal API key protection for group creation and score queries.
- KOLA AI score service integration with SHAP/anomaly fields and safe fallback scoring.
- Protected Squad gateway routes for transaction initiation/verification, virtual-account queries, dynamic virtual accounts, webhook error logs, and payout transfers.

## Setup

```powershell
cd kola_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your Supabase and Squad credentials.
Set `SQUAD_BENEFICIARY_ACCOUNT` to your 10-digit GTBank settlement account so group creation does not need to send `beneficiary_account` each time.

For local endpoint testing without calling Squad, set:

```env
SQUAD_MOCK_MODE=true
```

Squad sandbox base URL:

```env
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
```

KOLA AI service:

```env
KOLA_AI_URL=https://web-production-48a47.up.railway.app
KOLA_AI_KEY=kola-dev-key-2025
KOLA_AI_TIMEOUT_SECONDS=5
```

Run migrations:

```powershell
alembic upgrade head
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

## Docker

From the repository root:

```powershell
docker build -t kola-backend .
docker run --env-file .\kola_backend\.env -p 8000:8000 kola-backend
```

From this backend folder:

```powershell
docker build -t kola-backend .
docker run --env-file .env -p 8000:8000 kola-backend
```

For Render Docker deploys, either use the root `Dockerfile`, or set the Blueprint path to `kola_backend/render.yaml`.

Health check:

```powershell
curl http://127.0.0.1:8000/health
```

## Security

Squad webhooks must include an HMAC-SHA512 signature in `X-Squad-Signature`, `X-Signature`, or the older `X-Squad-Encrypted-Body` header.

For standard payment webhooks, the server checks the HMAC of the body using your Squad secret key. For virtual-account v2/v3 webhooks, it also checks this Squad signature string:

```text
transaction_reference|virtual_account_number|currency|principal_amount|settled_amount|customer_identifier
```

`WEBHOOK_SECRET` is optional. If it is empty, the backend uses `SQUAD_SECRET_KEY`, which matches Squad's webhook documentation.

The signature is verified before the request body is trusted or persisted. Invalid signatures receive `401`.

Group creation and score queries require:

```text
X-API-Key: <API_KEY from .env>
```

## Create Ajo Group

```powershell
curl -X POST http://127.0.0.1:8000/api/groups/ `
  -H "Content-Type: application/json" `
  -H "X-API-Key: replace_with_a_strong_internal_api_key" `
  -d '{
    "name": "Balogun Market Ajo",
    "description": "Weekly trader contribution group",
    "contribution_amount": "5000.00",
    "contribution_frequency": "weekly",
    "beneficiary_account": "4920299492",
    "members": [
      {
        "full_name": "Amina Bello",
        "phone": "08012345678",
        "email": "amina@example.com",
        "bvn": "22343211654",
        "dob": "07/19/1990",
        "gender": "2",
        "address": "22 Broad Street, Lagos"
      }
    ]
  }'
```

The response includes Squad virtual account details for each member. BVN and other KYC fields are sent to Squad for account creation but are not stored in KOLA's member table.

## Test Webhook Signature Locally

```powershell
$body = '{"event":"transaction.success","data":{"id":"evt_test_1","transaction_ref":"KOLA_TEST_REF","amount":500000,"currency":"NGN"}}'
$secret = "sk_test_your_secret_key"
$hmac = New-Object System.Security.Cryptography.HMACSHA512
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$signature = -join ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)) | ForEach-Object { $_.ToString("x2") })

curl -X POST http://127.0.0.1:8000/api/webhooks/squad `
  -H "Content-Type: application/json" `
  -H "X-Squad-Signature: $signature" `
  -d $body
```

If the payload contains a transaction reference, the API calls Squad transaction verify before storing the event.

## Score Query

```powershell
curl http://127.0.0.1:8000/api/scores/<member_id> `
  -H "X-API-Key: replace_with_a_strong_internal_api_key"
```

Response shape:

```json
{
  "member_id": "00000000-0000-0000-0000-000000000000",
  "kola_score": 714,
  "explanation": {},
  "verified_events_count": 23,
  "streak_weeks": 11,
  "last_updated": "2026-05-13T00:00:00Z",
  "events": []
}
```

If `KOLA_AI_URL` is configured, score queries call the AI service `POST /score` with Squad-verified events and return the XGBoost score, SHAP breakdown, anomaly fields, and confidence details. If the AI service is unavailable, KOLA keeps serving the fallback score instead of failing the lender query.

## Protected Squad Gateway

These routes require `X-API-Key` and call Squad with the backend secret key:

- `POST /api/squad/transactions/initiate`
- `GET /api/squad/transactions/{transaction_reference}/verify`
- `GET /api/squad/transactions`
- `GET /api/squad/wallet/balance`
- `GET /api/squad/virtual-accounts`
- `GET /api/squad/virtual-accounts/number/{virtual_account_number}`
- `GET /api/squad/virtual-accounts/customer/{customer_identifier}`
- `GET /api/squad/virtual-accounts/customer/{customer_identifier}/transactions`
- `GET /api/squad/virtual-accounts/webhook-error-logs`
- `DELETE /api/squad/virtual-accounts/webhook-error-logs/{transaction_reference}`
- `POST /api/squad/virtual-accounts/dynamic`
- `POST /api/squad/virtual-accounts/dynamic/initiate`
- `GET /api/squad/virtual-accounts/dynamic/{transaction_reference}/transactions`
- `POST /api/squad/virtual-accounts/simulate-payment`
- `POST /api/squad/transfers/account-lookup`
- `POST /api/squad/transfers`
- `POST /api/squad/transfers/{transaction_reference}/requery`
- `GET /api/squad/transfers`

## Notes For Production

- On Render, set `Root Directory` to `kola_backend`.
- Set `PYTHON_VERSION` to `3.11.11`, or keep the included `.python-version` file.
- Use `pip install -r requirements.txt` as the build command.
- Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the start command.
- Confirm the exact Squad virtual-account endpoint and response fields against the active Squad account.
- Add Redis-backed rate limiting for `/api/scores/*`.
- Move score recalculation into a durable background worker.
- Add integration tests with recorded Squad webhook fixtures.
