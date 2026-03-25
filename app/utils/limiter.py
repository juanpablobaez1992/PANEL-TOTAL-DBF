"""Limiter de rate limiting compartido para toda la aplicación."""

from __future__ import annotations

from slowapi import Limiter
from slowapi.util import get_remote_address

panel_limiter = Limiter(key_func=get_remote_address)
