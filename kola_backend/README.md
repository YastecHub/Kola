# KOLA Backend

FastAPI backend for KOLA, Nigeria's informal credit bureau for Ajo groups. Squad is treated as the source of truth for verified contribution and payment events.

## Implemented

- Async FastAPI app with SQLAlchemy 2.0 and Alembic.
- Supabase PostgreSQL configuration through `pydantic-settings`.
- Squad virtual account creation flow for group members.
- Squad webhook ingestion with HMAC-SHA512 verification for full-body and virtual-account v2/v3 signatures.
- Immutable economic event storage with raw payload and signature.
- Internal API key protection for group creation and score queries.
- Provisional score query API while the ML scoring service is pending.

## Setup

```powershell
cd kola_backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `.env` with your Supabase and Squad credentials.

For local endpoint testing without calling Squad, set:

```env
SQUAD_MOCK_MODE=true
```

Squad sandbox base URL:

```env
SQUAD_BASE_URL=https://sandbox-api-d.squadco.com
```

Run migrations:

```powershell
alembic upgrade head
```

Start the API:

```powershell
uvicorn app.main:app --reload
```

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

## Notes For Production

- On Render, set `Root Directory` to `kola_backend`.
- Use `pip install -r requirements.txt` as the build command.
- Use `uvicorn app.main:app --host 0.0.0.0 --port $PORT` as the start command.
- Confirm the exact Squad virtual-account endpoint and response fields against the active Squad account.
- Add Redis-backed rate limiting for `/api/scores/*`.
- Move score recalculation into a durable background worker.
- Add integration tests with recorded Squad webhook fixtures.
