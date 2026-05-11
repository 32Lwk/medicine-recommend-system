"""チャット POST 用のフレームワーク非依存クライアント情報。"""

from __future__ import annotations

from dataclasses import dataclass


def _first_forwarded_client_ip(x_forwarded_for: str | None) -> str | None:
    if not x_forwarded_for or not str(x_forwarded_for).strip():
        return None
    return str(x_forwarded_for).split(",", maxsplit=1)[0].strip() or None


def resolve_client_ip(*, x_forwarded_for: str | None, direct: str | None) -> str:
    """
    リバースプロキシ経由では X-Forwarded-For の先頭がクライアント IP（Render / nginx 等の一般的な付与順）。
    direct はフォールバック（ローカルでは remote_addr や request.client.host）。
    """
    ip = _first_forwarded_client_ip(x_forwarded_for)
    if ip:
        return ip
    return (direct or "").strip() or ""


@dataclass(frozen=True)
class ChatClientInfo:
    client_ip: str
    user_agent: str

    @classmethod
    def from_starlette_request(cls, request) -> ChatClientInfo:
        """Starlette / FastAPI の Request から同様に組み立てる。"""
        xff = request.headers.get("x-forwarded-for") or request.headers.get("X-Forwarded-For")
        direct = request.client.host if request.client else None
        ip = resolve_client_ip(x_forwarded_for=xff, direct=direct)
        ua = (request.headers.get("user-agent") or "").strip()
        return cls(client_ip=ip, user_agent=ua)
