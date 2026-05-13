from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

import httpx
from loguru import logger

from app.core.config import settings
from app.utils.hmac import verify_hmac_sha512


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
    ) -> VirtualAccountResult:
        first_name, _, last_name = full_name.partition(" ")
        payload = {
            "first_name": first_name,
            "last_name": last_name or first_name,
            "mobile_num": phone,
            "email": email,
            "customer_identifier": customer_identifier,
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

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        return verify_hmac_sha512(settings.webhook_secret, payload, signature)

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
