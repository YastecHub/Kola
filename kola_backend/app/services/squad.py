from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import re
import uuid
from typing import Any
from urllib.parse import urljoin

import httpx
from loguru import logger

from app.core.config import settings
from app.utils.hmac import compute_hmac_sha512, normalize_signature, verify_hmac_sha512


class SquadError(RuntimeError):
    def __init__(
        self,
        message: str,
        *,
        status_code: int | None = None,
        response_body: dict[str, Any] | str | None = None,
        upstream_url: str | None = None,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.response_body = response_body
        self.upstream_url = upstream_url


@dataclass(slots=True)
class VirtualAccountResult:
    va_id: str | None
    account_number: str | None
    bank_name: str | None
    customer_id: str | None
    raw: dict[str, Any]


class SquadService:
    def __init__(self, client: httpx.AsyncClient | None = None) -> None:
        self._client = client

    @property
    def headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {settings.squad_secret_key}",
            "Content-Type": "application/json",
        }

    async def _request(
        self,
        method: str,
        path: str,
        json: dict[str, Any] | None = None,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        base_url = settings.squad_api_base_url
        if not settings.is_squad_base_url_supported:
            logger.warning(
                "Unsupported SQUAD_BASE_URL configured: {}; using {}",
                settings.squad_configured_base_url,
                base_url,
            )
        client = self._client or httpx.AsyncClient(base_url=base_url, timeout=30)
        close_client = self._client is None
        upstream_url = urljoin(f"{base_url}/", path.lstrip("/"))
        try:
            response = await client.request(method, path, headers=self.headers, json=json, params=params)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            try:
                response_body: dict[str, Any] | str = exc.response.json()
            except ValueError:
                response_body = exc.response.text
            logger.error("Squad API rejected request: status={} body={}", exc.response.status_code, response_body)
            raise SquadError(
                "Squad API request failed",
                status_code=exc.response.status_code,
                response_body=response_body,
                upstream_url=str(exc.request.url),
            ) from exc
        except httpx.HTTPError as exc:
            logger.exception("Squad API transport error")
            raise SquadError("Unable to reach Squad API", upstream_url=upstream_url) from exc
        finally:
            if close_client:
                await client.aclose()
        return data

    async def create_virtual_account(
        self,
        *,
        full_name: str,
        phone: str,
        email: str | None,
        customer_identifier: str,
        middle_name: str | None = None,
        bvn: str | None = None,
        dob: str | None = None,
        gender: str | None = None,
        address: str | None = None,
        beneficiary_account: str | None = None,
    ) -> VirtualAccountResult:
        if settings.squad_mock_mode:
            return self._mock_virtual_account(customer_identifier)

        first_name, _, last_name = full_name.partition(" ")
        payload = {
            "first_name": first_name,
            "last_name": last_name or first_name,
            "middle_name": _clean_optional_text(middle_name),
            "mobile_num": phone,
            "email": email,
            "bvn": _clean_bvn(bvn),
            "dob": _clean_dob(dob),
            "gender": _clean_gender(gender),
            "address": _clean_optional_text(address),
            "customer_identifier": customer_identifier,
            "beneficiary_account": _clean_account_number(beneficiary_account or settings.squad_beneficiary_account),
        }
        payload = {key: value for key, value in payload.items() if value is not None}
        data = await self._request("POST", "/virtual-account", json=payload)
        body = data.get("data") or data
        account = body.get("virtual_account") or body.get("account") or body

        return VirtualAccountResult(
            va_id=str(account.get("id") or account.get("virtual_account_id") or "") or None,
            account_number=account.get("account_number") or account.get("virtual_account_number"),
            bank_name=account.get("bank_name") or account.get("bank"),
            customer_id=str(body.get("customer_id") or account.get("customer_id") or customer_identifier),
            raw=data,
        )

    def _mock_virtual_account(self, customer_identifier: str) -> VirtualAccountResult:
        suffix = str(abs(hash(customer_identifier)))[:8].zfill(8)
        return VirtualAccountResult(
            va_id=f"mock_va_{uuid.uuid4().hex[:12]}",
            account_number=f"99{suffix}"[:10],
            bank_name="KOLA Mock Bank",
            customer_id=customer_identifier,
            raw={"mock": True, "customer_identifier": customer_identifier},
        )

    def verify_webhook_signature(
        self,
        payload: bytes,
        signature: str,
        parsed_payload: dict[str, Any] | None = None,
    ) -> bool:
        secret = settings.squad_webhook_secret
        if verify_hmac_sha512(secret, payload, signature):
            return True

        if parsed_payload is not None:
            compact_json = json.dumps(parsed_payload, separators=(",", ":"), ensure_ascii=False)
            if compute_hmac_sha512(secret, compact_json) == normalize_signature(signature):
                return True

            pipe_signature = self._virtual_account_signature_string(parsed_payload)
            if pipe_signature and compute_hmac_sha512(secret, pipe_signature) == normalize_signature(signature):
                return True

        return False

    def _virtual_account_signature_string(self, payload: dict[str, Any]) -> str | None:
        required_fields = (
            "transaction_reference",
            "virtual_account_number",
            "currency",
            "principal_amount",
            "settled_amount",
            "customer_identifier",
        )
        if not all(payload.get(field) is not None for field in required_fields):
            return None
        return "|".join(str(payload[field]) for field in required_fields)

    async def verify_transaction(self, transaction_reference: str) -> dict[str, Any]:
        if not transaction_reference:
            raise SquadError("Missing transaction reference")
        return await self._request("GET", f"/transaction/verify/{transaction_reference}")

    async def initiate_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/transaction/initiate", json=payload)

    async def query_transactions(self, params: dict[str, Any]) -> dict[str, Any]:
        return await self._request("GET", "/transaction", params=params)

    async def get_wallet_balance(self, currency_id: str = "NGN") -> dict[str, Any]:
        return await self._request("GET", "/merchant/balance", params={"currency_id": currency_id})

    async def get_virtual_account_by_number(self, virtual_account_number: str) -> dict[str, Any]:
        return await self._request("GET", f"/virtual-account/customer/{virtual_account_number}")

    async def get_virtual_account_by_customer_identifier(self, customer_identifier: str) -> dict[str, Any]:
        return await self._request("GET", f"/virtual-account/{customer_identifier}")

    async def list_merchant_virtual_accounts(self, page: int = 1, per_page: int = 50) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/virtual-account/merchant/accounts",
            params={"page": page, "perPage": per_page},
        )

    async def list_customer_virtual_account_transactions(self, customer_identifier: str) -> dict[str, Any]:
        return await self._request("GET", f"/virtual-account/customer/transactions/{customer_identifier}")

    async def get_webhook_error_logs(self, page: int = 1, per_page: int = 100) -> dict[str, Any]:
        return await self._request(
            "GET",
            "/virtual-account/webhook/logs",
            params={"page": page, "perPage": per_page},
        )

    async def delete_webhook_error_log(self, transaction_reference: str) -> dict[str, Any]:
        return await self._request("DELETE", f"/virtual-account/webhook/logs/{transaction_reference}")

    async def create_dynamic_virtual_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/virtual-account/create-dynamic-virtual-account", json=payload)

    async def initiate_dynamic_virtual_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/virtual-account/initiate-dynamic-virtual-account", json=payload)

    async def get_dynamic_virtual_account_transactions(self, transaction_reference: str) -> dict[str, Any]:
        return await self._request(
            "GET",
            f"/virtual-account/get-dynamic-virtual-account-transactions/{transaction_reference}",
        )

    async def simulate_virtual_account_payment(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/virtual-account/simulate/payment", json=payload)

    async def lookup_bank_account(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/payout/account/lookup", json=payload)

    async def create_transfer(self, payload: dict[str, Any]) -> dict[str, Any]:
        return await self._request("POST", "/payout/transfer", json=payload)

    async def requery_transfer(self, transaction_reference: str) -> dict[str, Any]:
        return await self._request("POST", "/payout/requery", json={"transaction_reference": transaction_reference})

    async def list_transfers(self, page: int = 1, per_page: int = 50, direction: str = "DESC") -> dict[str, Any]:
        return await self._request(
            "GET",
            "/payout/list",
            params={"page": page, "perPage": per_page, "dir": direction},
        )


def parse_amount(value: Any) -> Decimal | None:
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value))
    except Exception:
        return None
    if decimal_value > 100_000_000 and decimal_value == decimal_value.to_integral_value():
        return decimal_value / Decimal("100")
    return decimal_value


def _clean_optional_text(value: str | None) -> str | None:
    if value is None:
        return None
    value = value.strip()
    if not value or value.lower() == "string":
        return None
    return value


def _clean_bvn(value: str | None) -> str | None:
    value = _clean_optional_text(value)
    if value is None:
        return None
    return value if re.fullmatch(r"\d{11}", value) else None


def _clean_dob(value: str | None) -> str | None:
    value = _clean_optional_text(value)
    if value is None:
        return None
    return value if re.fullmatch(r"\d{2}/\d{2}/\d{4}", value) else None


def _clean_gender(value: str | None) -> str | None:
    value = _clean_optional_text(value)
    if value is None:
        return None
    return value if value in {"1", "2"} else None


def _clean_account_number(value: str | None) -> str | None:
    value = _clean_optional_text(value)
    if value is None:
        return None
    return value if re.fullmatch(r"\d{10}", value) else None
