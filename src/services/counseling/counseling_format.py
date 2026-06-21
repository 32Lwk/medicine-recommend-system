"""
会話履歴の整形（format_conversation_history）

generate_counseling_response 等から参照されるため、循環参照回避のため単独モジュールに配置。
"""
from typing import Dict, List


def format_conversation_history(messages: List[Dict]) -> str:
    """
    会話履歴をテキスト形式に整形

    Args:
        messages: メッセージリスト

    Returns:
        整形された会話履歴テキスト
    """
    history_text = ""
    for msg in messages:
        role = msg.get("type", "user")
        content = msg.get("content", "")
        if role == "user":
            history_text += f"ユーザー: {content}\n"
        elif role == "bot":
            history_text += f"ボット: {content}\n"
    return history_text


def combine_counseling_message(response: str, question: str | None = None) -> str:
    """応援メッセージとフォローアップ質問を1つの返信にまとめる。"""
    response = (response or "").strip()
    question = (question or "").strip()
    if question:
        return f"{response}\n\n{question}"
    return response
