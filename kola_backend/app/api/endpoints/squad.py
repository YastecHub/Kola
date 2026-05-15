from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status

from app.core.config import settings
from app.core.security import require_api_key
from app.services.squad import SquadError, SquadService

router = APIRouter(dependencies=[Depends(require_api_key)])


def _squad_error(exc: SquadError) -> HTTPException:
    detail: dict[str, object] = {"message": exc.message}
    if exc.status_code is not None:
        detail["squad_status_code"] = exc.status_code
    if exc.response_body is not None:
        detail["squad_response"] = exc.response_body
    if exc.upstream_url is not None:
        detail["upstream_url"] = exc.upstream_url
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=detail,
    )


@router.get("/config")
async def get_squad_config() -> dict[str, Any]:
    return {
        "configured_base_url": settings.squad_configured_base_url,
        "effective_base_url": settings.squad_api_base_url,
        "base_url_supported": settings.is_squad_base_url_supported,
        "mock_mode": settings.squad_mock_mode,
        "secret_key_prefix": settings.squad_secret_key[:12],
        "public_key_prefix": settings.squad_public_key[:12],
    }


@router.post("/transactions/initiate")
async def initiate_payment(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await SquadService().initiate_payment(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/transactions/{transaction_reference}/verify")
async def verify_transaction(transaction_reference: str) -> dict[str, Any]:
    try:
        return await SquadService().verify_transaction(transaction_reference)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/transactions")
async def query_transactions(
    currency: str = "NGN",
    start_date: str | None = None,
    end_date: str | None = None,
    page: int = Query(1, ge=1),
    perpage: int = Query(50, ge=1, le=100),
    reference: str | None = None,
) -> dict[str, Any]:
    params = {
        "currency": currency,
        "page": page,
        "perpage": perpage,
    }
    if start_date:
        params["start_date"] = start_date
    if end_date:
        params["end_date"] = end_date
    if reference:
        params["reference"] = reference

    try:
        return await SquadService().query_transactions(params)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/wallet/balance")
async def get_wallet_balance(currency_id: str = "NGN") -> dict[str, Any]:
    try:
        return await SquadService().get_wallet_balance(currency_id)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts/number/{virtual_account_number}")
async def get_virtual_account_by_number(virtual_account_number: str) -> dict[str, Any]:
    try:
        return await SquadService().get_virtual_account_by_number(virtual_account_number)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts/customer/{customer_identifier}")
async def get_virtual_account_by_customer_identifier(customer_identifier: str) -> dict[str, Any]:
    try:
        return await SquadService().get_virtual_account_by_customer_identifier(customer_identifier)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts")
async def list_merchant_virtual_accounts(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return await SquadService().list_merchant_virtual_accounts(page=page, per_page=per_page)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts/customer/{customer_identifier}/transactions")
async def list_customer_virtual_account_transactions(customer_identifier: str) -> dict[str, Any]:
    try:
        return await SquadService().list_customer_virtual_account_transactions(customer_identifier)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts/webhook-error-logs")
async def get_webhook_error_logs(
    page: int = Query(1, ge=1),
    per_page: int = Query(100, ge=1, le=100),
) -> dict[str, Any]:
    try:
        return await SquadService().get_webhook_error_logs(page=page, per_page=per_page)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.delete("/virtual-accounts/webhook-error-logs/{transaction_reference}")
async def delete_webhook_error_log(transaction_reference: str) -> dict[str, Any]:
    try:
        return await SquadService().delete_webhook_error_log(transaction_reference)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/virtual-accounts/dynamic")
async def create_dynamic_virtual_account(payload: dict[str, Any] = Body(default_factory=dict)) -> dict[str, Any]:
    try:
        return await SquadService().create_dynamic_virtual_account(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/virtual-accounts/dynamic/initiate")
async def initiate_dynamic_virtual_account(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await SquadService().initiate_dynamic_virtual_account(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/virtual-accounts/dynamic/{transaction_reference}/transactions")
async def get_dynamic_virtual_account_transactions(transaction_reference: str) -> dict[str, Any]:
    try:
        return await SquadService().get_dynamic_virtual_account_transactions(transaction_reference)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/virtual-accounts/simulate-payment")
async def simulate_virtual_account_payment(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await SquadService().simulate_virtual_account_payment(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/transfers/account-lookup")
async def lookup_bank_account(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await SquadService().lookup_bank_account(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/transfers")
async def create_transfer(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    try:
        return await SquadService().create_transfer(payload)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.post("/transfers/{transaction_reference}/requery")
async def requery_transfer(transaction_reference: str) -> dict[str, Any]:
    try:
        return await SquadService().requery_transfer(transaction_reference)
    except SquadError as exc:
        raise _squad_error(exc) from exc


@router.get("/transfers")
async def list_transfers(
    page: int = Query(1, ge=1),
    per_page: int = Query(50, ge=1, le=100),
    direction: str = Query("DESC", pattern="^(ASC|DESC|asc|desc)$"),
) -> dict[str, Any]:
    try:
        return await SquadService().list_transfers(page=page, per_page=per_page, direction=direction.upper())
    except SquadError as exc:
        raise _squad_error(exc) from exc
