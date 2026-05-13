from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
import json
import uuid
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.utils.hmac import compute_hmac_sha512, normalize_signature, verify_hmac_sha512


class SquadError(RuntimeError):
    pass


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

    async def _request(self, method: str, path: str, json: dict[str, Any] | None = None) -> dict[str, Any]:
        client = self._client or httpx.AsyncClient(base_url=str(settings.squad_base_url), timeout=30)
        close_client = self._client is None
        try:
            response = await client.request(method, path, headers=self.headers, json=json)
            response.raise_for_status()
            data: dict[str, Any] = response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Squad API rejected request: status={} body={}", exc.response.status_code, exc.response.text)
            raise SquadError("Squad API request failed") from exc
        except httpx.HTTPError as exc:
            logger.exception("Squad API transport error")
            raise SquadError("Unable to reach Squad API") from exc
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
            "middle_name": middle_name,
            "mobile_num": phone,
            "email": email,
            "bvn": bvn,
            "dob": dob,
            "gender": gender,
            "address": address,
            "customer_identifier": customer_identifier,
            "beneficiary_account": beneficiary_account or settings.squad_beneficiary_account,
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
