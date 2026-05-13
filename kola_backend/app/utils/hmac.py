from __future__ import annotations

import hmac
from hashlib import sha512


def compute_hmac_sha512(secret: str, payload: bytes) -> str:
    return hmac.new(secret.encode("utf-8"), payload, sha512).hexdigest()


def verify_hmac_sha512(secret: str, payload: bytes, signature: str) -> bool:
    expected = compute_hmac_sha512(secret, payload)
    provided = signature.lower().removeprefix("sha512=").strip()
    return hmac.compare_digest(expected, provided)
