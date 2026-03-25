"""Helpers mínimos para firmar requests OAuth 1.0a."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets
import time
from typing import Any
from urllib.parse import parse_qsl, quote, urlencode, urlparse


def _percent_encode(value: str) -> str:
    return quote(value, safe="~-._")


def _normalize_params(params: dict[str, Any]) -> str:
    items: list[tuple[str, str]] = []
    for key, value in params.items():
        if value is None:
            continue
        if isinstance(value, (list, tuple)):
            for item in value:
                items.append((_percent_encode(str(key)), _percent_encode(str(item))))
        else:
            items.append((_percent_encode(str(key)), _percent_encode(str(value))))
    items.sort()
    return "&".join(f"{key}={value}" for key, value in items)


def build_oauth1_header(
    *,
    method: str,
    url: str,
    consumer_key: str,
    consumer_secret: str,
    token: str,
    token_secret: str,
    extra_params: dict[str, Any] | None = None,
) -> str:
    """Genera el header Authorization para OAuth 1.0a HMAC-SHA1."""

    parsed = urlparse(url)
    base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
    query_params = dict(parse_qsl(parsed.query, keep_blank_values=True))
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": secrets.token_hex(16),
        "oauth_signature_method": "HMAC-SHA1",
        "oauth_timestamp": str(int(time.time())),
        "oauth_token": token,
        "oauth_version": "1.0",
    }
    signature_params = oauth_params | query_params | (extra_params or {})
    normalized_params = _normalize_params(signature_params)
    signature_base = "&".join(
        [
            method.upper(),
            _percent_encode(base_url),
            _percent_encode(normalized_params),
        ]
    )
    signing_key = f"{_percent_encode(consumer_secret)}&{_percent_encode(token_secret)}"
    digest = hmac.new(
        signing_key.encode("utf-8"),
        signature_base.encode("utf-8"),
        hashlib.sha1,
    ).digest()
    oauth_params["oauth_signature"] = base64.b64encode(digest).decode("utf-8")

    header_params = ", ".join(
        f'{_percent_encode(key)}="{_percent_encode(value)}"'
        for key, value in sorted(oauth_params.items())
    )
    return f"OAuth {header_params}"
