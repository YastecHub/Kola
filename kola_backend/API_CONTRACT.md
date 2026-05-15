# KOLA Backend API Contract

Base URL for local development:

```text
http://127.0.0.1:8001
```

For local frontend testing without calling Squad, set this in `.env`:

```env
SQUAD_MOCK_MODE=true
```

Interactive docs:

```text
http://127.0.0.1:8001/docs
```

## Auth

Frontend/internal clients must send this header for protected endpoints:

```text
X-API-Key: <API_KEY from backend .env>
```

Do not send this key from a public production frontend. In production, the frontend should call your own trusted backend/session layer, or you should replace this with user auth.

## Health

```http
GET /health
```

Response:

```json
{
  "status": "ok",
  "environment": "development"
}
```

## Create Ajo Group And Virtual Accounts

```http
POST /api/groups/
X-API-Key: <api-key>
Content-Type: application/json
```

Request:

```json
{
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
}
```

Response:

```json
{
  "id": "group-uuid",
  "name": "Balogun Market Ajo",
  "description": "Weekly trader contribution group",
  "contribution_amount": "5000.00",
  "contribution_frequency": "weekly",
  "created_at": "2026-05-13T10:00:00Z",
  "members": [
    {
      "id": "member-uuid",
      "group_id": "group-uuid",
      "full_name": "Amina Bello",
      "phone": "08012345678",
      "email": "amina@example.com",
      "squad_customer_id": "customer-id",
      "squad_va_id": "virtual-account-id",
      "squad_va_number": "1234567890",
      "squad_va_bank": "Wema Bank",
      "created_at": "2026-05-13T10:00:00Z"
    }
  ]
}
```

## Squad Webhook

This endpoint is called by Squad, not the frontend.

```http
POST /api/webhooks/squad
X-Squad-Signature: <hmac-signature>
Content-Type: application/json
```

The backend verifies the signature before storing the event.

Local PowerShell test:

```powershell
$body = '{"transaction_reference":"KOLA_TEST_REF_001","virtual_account_number":"9947963138","currency":"NGN","principal_amount":"5000","settled_amount":"4975","customer_identifier":"ec66f4db-9ca2-4d5c-9592-273b043834db","transaction_date":"2026-05-13T20:00:00Z"}'
$secret = "sk_test_your_secret_key"
$hmac = New-Object System.Security.Cryptography.HMACSHA512
$hmac.Key = [Text.Encoding]::UTF8.GetBytes($secret)
$signature = -join ($hmac.ComputeHash([Text.Encoding]::UTF8.GetBytes($body)) | ForEach-Object { $_.ToString("x2") })

curl.exe -X POST "http://127.0.0.1:8001/api/webhooks/squad" `
  -H "Content-Type: application/json" `
  -H "X-Squad-Signature: $signature" `
  --data-raw $body
```

Use the same secret as `WEBHOOK_SECRET`, or `SQUAD_SECRET_KEY` if `WEBHOOK_SECRET` is empty.

## Get Score By Member ID

```http
GET /api/scores/{member_id}
X-API-Key: <api-key>
```

Response:

```json
{
  "member_id": "member-uuid",
  "kola_score": 714,
  "explanation": {
    "basis": "xgboost_shap",
    "shap": { "streak": 18, "catchup": 8, "amount_std": 28, "collector": 14, "trade": 12 },
    "anomaly_flag": false,
    "anomaly_reason": null,
    "confidence": "High",
    "confidence_detail": "13 weeks Squad-verified"
  },
  "verified_events_count": 23,
  "streak_weeks": 11,
  "last_updated": "2026-05-13T10:00:00Z",
  "events": []
}
```

## Get Score By Trader Phone Or ID

```http
GET /api/scores/trader/{phone_or_id}
X-API-Key: <api-key>
```

Example:

```text
GET /api/scores/trader/08012345678
```

## Protected Squad Gateway

All routes below require:

```http
X-API-Key: <api-key>
```

They proxy relevant Squad APIs through the backend so the frontend/demo never exposes the Squad secret key.

```http
GET /api/squad/config
POST /api/squad/transactions/initiate
GET /api/squad/transactions/{transaction_reference}/verify
GET /api/squad/transactions?currency=NGN&start_date=2026-05-01&end_date=2026-05-15&page=1&perpage=50
GET /api/squad/wallet/balance?currency_id=NGN

GET /api/squad/virtual-accounts
GET /api/squad/virtual-accounts/number/{virtual_account_number}
GET /api/squad/virtual-accounts/customer/{customer_identifier}
GET /api/squad/virtual-accounts/customer/{customer_identifier}/transactions
GET /api/squad/virtual-accounts/webhook-error-logs
DELETE /api/squad/virtual-accounts/webhook-error-logs/{transaction_reference}

POST /api/squad/virtual-accounts/dynamic
POST /api/squad/virtual-accounts/dynamic/initiate
GET /api/squad/virtual-accounts/dynamic/{transaction_reference}/transactions
POST /api/squad/virtual-accounts/simulate-payment

POST /api/squad/transfers/account-lookup
POST /api/squad/transfers
POST /api/squad/transfers/{transaction_reference}/requery
GET /api/squad/transfers
```

The request and response bodies mirror Squad's official API payloads.
