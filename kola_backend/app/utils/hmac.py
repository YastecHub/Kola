from __future__ import annotations

import hmac
from hashlib import sha512


def compute_hmac_sha512(secret: str, payload: bytes | str) -> str:
    payload_bytes = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hmac.new(secret.encode("utf-8"), payload_bytes, sha512).hexdigest()


def verify_hmac_sha512(secret: str, payload: bytes, signature: str) -> bool:
    expected = compute_hmac_sha512(secret, payload)
    provided = normalize_signature(signature)
    return hmac.compare_digest(expected, provided)


def normalize_signature(signature: str) -> str:
    return signature.lower().removeprefix("sha512=").strip()
