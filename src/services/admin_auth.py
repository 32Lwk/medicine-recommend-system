"""管理画面の Cookie 認証（Cursor Simple Browser 等で Basic 認証が使えない場合向け）。"""
from __future__ import annotations

import hashlib
import hmac
import os

ADMIN_COOKIE_NAME = "admin_auth"


def admin_password() -> str:
    pwd = (os.getenv("ADMIN_PASSWORD") or "").strip()
    return pwd if pwd else "admin123"


def _signing_secret() -> str:
    return (
        (os.getenv("SECRET_KEY") or "").strip()
        or admin_password()
        or "dev-admin-secret"
    )


def create_admin_token() -> str:
    secret = _signing_secret()
    return hmac.new(secret.encode(), b"admin_session", hashlib.sha256).hexdigest()


def verify_admin_token(token: str | None) -> bool:
    if not token:
        return False
    expected = create_admin_token()
    return hmac.compare_digest(token, expected)


def credentials_match(username: str | None, password: str | None) -> bool:
    return username == "admin" and password == admin_password()
