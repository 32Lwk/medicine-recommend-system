"""
LLM モデル・API 設定の集約（環境変数で上書き可能）
"""
import os

from config.settings import _get_int


def _get_float(key: str, default: float) -> float:
    val = os.getenv(key)
    if val is None:
        return default
    try:
        return float(val)
    except ValueError:
        return default


def _get_bool(key: str, default: bool) -> bool:
    val = os.getenv(key)
    if val is None:
        return default
    return val.strip().lower() in ("1", "true", "yes", "on")


# プロファイル: legacy | gpt5（未設定時は gpt5。切り戻しは LLM_MODEL_PROFILE=legacy）
LLM_MODEL_PROFILE = (os.getenv("LLM_MODEL_PROFILE") or "gpt5").strip().lower()

_LEGACY = {
    "triage": "gpt-4o-mini",
    "nlu": "gpt-4o-mini",
    "counsel": "gpt-4o-mini",
    "concierge": "gpt-4o-mini",
    "concierge_greeting": "gpt-4o-mini",
    "emoji_intent": "gpt-4o-mini",
    "explain": "gpt-4o",
    "ask": "gpt-4o-mini",
    "admin": "gpt-4o-mini",
    "validator": "gpt-4o-mini",
}

_GPT5 = {
    "triage": "gpt-5.4-mini",
    "nlu": "gpt-5.4-mini",
    "counsel": "gpt-5.4-mini",
    "concierge": "gpt-5.4-mini",
    "concierge_greeting": "gpt-4o-mini",
    "emoji_intent": "gpt-4o-mini",
    "explain": "gpt-5.4",
    "ask": "gpt-5.4-mini",
    "admin": "gpt-5.4-mini",
    "store": "gpt-5.4-mini",
    "moderation": "gpt-5.4-mini",
    "validator": "gpt-5.4-mini",
}

RESPONSES_API_ROLES = frozenset({"triage", "explain"})

_PROFILE_MODELS = _GPT5 if LLM_MODEL_PROFILE == "gpt5" else _LEGACY


def get_model(role: str) -> str:
    """role: triage | nlu | counsel | concierge | concierge_greeting | explain | ask | admin"""
    try:
        from config.llm_runtime import get_request_profile
        req_profile = get_request_profile()
        if req_profile == "gpt5":
            return _GPT5.get(role, _GPT5["triage"])
        if req_profile == "legacy":
            return _LEGACY.get(role, _LEGACY["triage"])
    except ImportError:
        pass
    env_key = f"OPENAI_MODEL_{role.upper()}"
    override = os.getenv(env_key)
    if override:
        return override.strip()
    return _PROFILE_MODELS.get(role, _LEGACY["triage"])


def get_explain_model(is_high_risk: bool) -> str | None:
    """低リスク症状の説明生成に使う高速モデル名を返す（Phase 1 レイテンシ）。

    - フラグ OFF もしくは高リスク → None（呼び出し側は既定の explain モデル= gpt-5.4 を使用）
    - 低リスク かつ フラグ ON → 高速モデル（gpt5 プロファイル: gpt-5.4-mini / legacy: gpt-4o-mini）

    高リスクの判定は呼び出し側（説明生成）で行う。ここではモデル名の解決のみ。
    """
    try:
        from config.llm_flags import is_explain_fast_lowrisk_enabled
    except ImportError:
        return None
    if is_high_risk or not is_explain_fast_lowrisk_enabled():
        return None
    override = os.getenv("OPENAI_MODEL_EXPLAIN_FAST")
    if override:
        return override.strip()
    # mini 系（プロファイル準拠）。nlu ロールは両プロファイルとも mini。
    return _PROFILE_MODELS.get("nlu", _LEGACY["nlu"])


def use_responses_api() -> bool:
    return _get_bool("OPENAI_USE_RESPONSES_API", False)


def use_responses_api_for_role(role: str) -> bool:
    if use_responses_api():
        return True
    return role in RESPONSES_API_ROLES


_ROLE_TIMEOUT_SEC = {
    "triage": 8.0,
    "explain": 60.0,
    "counsel": 20.0,
    "concierge": 12.0,
    "concierge_greeting": 12.0,
    "emoji_intent": 8.0,
    "moderation": 8.0,
    "nlu": 15.0,
    "ask": 20.0,
    "store": 15.0,
}


def get_role_timeout_sec(role: str) -> float:
    return _ROLE_TIMEOUT_SEC.get(role, 30.0)


def get_explain_batch_hard_timeout_sec() -> float:
    """バッチ使用上の注意 LLM 全体の上限（SSE 180s 以内に収める）。"""
    return _get_float("EXPLAIN_BATCH_HARD_TIMEOUT_SEC", 90.0)


def get_explain_empty_retry_max_latency_sec() -> float:
    """空応答リトライは初回がこの秒数未満のときのみ（タイムアウト後の二重 60s を防ぐ）。"""
    return _get_float("EXPLAIN_EMPTY_RETRY_MAX_LATENCY_SEC", 20.0)


def get_reasoning_effort(role: str = "triage") -> str:
    key = f"OPENAI_REASONING_EFFORT_{role.upper()}"
    return (os.getenv(key) or os.getenv("OPENAI_REASONING_EFFORT_TRIAGE") or "low").strip()


def get_text_verbosity(role: str = "explain") -> str:
    key = f"OPENAI_TEXT_VERBOSITY_{role.upper()}"
    return (os.getenv(key) or "medium").strip()


# 予算（OpenAI API 費用のみ・円）
OPENAI_MONTHLY_BUDGET_JPY = _get_int("OPENAI_MONTHLY_BUDGET_JPY", 50000)
OPENAI_SESSION_COST_ALERT_JPY = _get_float("OPENAI_SESSION_COST_ALERT_JPY", 15.0)


def get_openai_api_key() -> str | None:
    app_env = (os.getenv("APP_ENV") or "").strip().lower()
    if app_env in ("staging", "development", "dev", "local", "test"):
        return os.getenv("OPENAI_API_KEY_STAGING") or os.getenv("OPENAI_API_KEY")
    return os.getenv("OPENAI_API_KEY_PRODUCTION") or os.getenv("OPENAI_API_KEY")
