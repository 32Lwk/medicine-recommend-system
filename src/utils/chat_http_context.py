"""チャット POST 用のフレームワーク非依存クライアント情報。"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ChatClientInfo:
    client_ip: str
    user_agent: str
