"""
アプリケーション初期化設定の集約

ログ設定、環境変数読み込み、CORS・セッション設定を提供する。
"""
import os
import logging


def load_env() -> bool:
    """
    .envファイルから環境変数を読み込む。
    明示的パスで試行後、引数なしで自動検索も試行する。

    Returns:
        bool: 読み込み成功時True
    """
    try:
        from dotenv import load_dotenv

        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        env_path = os.path.join(base_dir, '.env')
        log = logging.getLogger(__name__)

        if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
            log.debug(f"[app_config] base_dir: {base_dir}")
            log.debug(f"[app_config] .env path: {env_path}")
            log.debug(f"[app_config] .env exists: {os.path.exists(env_path)}")

        # プロジェクトルートの .env を最優先。ここで読めた場合は cwd 探索をしない
        # （ルートに APP_ENV=production があるのに、別ディレクトリの .env が上書きする事故を防ぐ）
        loaded = False
        if os.path.exists(env_path):
            loaded = load_dotenv(env_path, override=True)
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                log.debug(f"[app_config] load_dotenv({env_path}) result: {loaded}")
        else:
            loaded = load_dotenv(override=True)
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                log.debug(f"[app_config] load_dotenv() (no args) result: {loaded}")

        if os.getenv('OPENAI_API_KEY'):
            if os.getenv('DEBUG_MODE', 'false').lower() == 'true':
                log.debug("[app_config] OPENAI_API_KEY loaded successfully")
        else:
            log.warning("[app_config] WARNING: OPENAI_API_KEY not set in environment")

        log.info("[app_config] Environment variables loaded from .env")
        return loaded
    except ImportError:
        logging.getLogger(__name__).info(
            "[app_config] python-dotenv not installed. Using environment variables only."
        )
        return False
    except Exception as e:
        logging.getLogger(__name__).warning(f"[app_config] .env load error: {e}")
        import traceback
        traceback.print_exc()
        return False


def configure_logging(log_dir: str = None) -> None:
    """
    ログ設定を行う。
    log_dirが未指定の場合はプロジェクトルートのlog/を使用する。

    Args:
        log_dir: ログファイルの出力ディレクトリ
    """
    if log_dir is None:
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        log_dir = os.path.join(base_dir, 'log')

    os.makedirs(log_dir, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.StreamHandler(),
            logging.FileHandler(os.path.join(log_dir, 'app.log'), encoding='utf-8'),
        ],
    )


def _normalized_app_env() -> str:
    """APP_ENV の BOM・余分な空白・外側クォートを除いた小文字トークン。"""
    raw = (os.getenv("APP_ENV") or "").replace("\ufeff", "").strip()
    if len(raw) >= 2 and raw[0] == raw[-1] and raw[0] in "\"'":
        raw = raw[1:-1].strip()
    return raw.lower()


def is_development_runtime() -> bool:
    """
    開発向けUI（オンボーディングの dev スライド、DEV バッジ等）および
    セッション Cookie の本番扱いの判定に使う。

    優先順位:
    1. APP_ENV が明示されていればそれに従う（production なら本番）。
    2. 未設定時は代表的なホスティングの本番シグナル（VERCEL_ENV / RAILWAY_ENVIRONMENT / Render 本番サービス）で本番扱い。
    3. それ以外（ローカルや不明なデプロイ）は開発扱い。

    Render の PR プレビュー（IS_PULL_REQUEST=true）のみ開発扱いとする。
    """
    raw = _normalized_app_env()
    if raw == "production":
        return False
    if raw in ("development", "dev", "local", "staging", "test"):
        return True
    if raw:
        return True

    if os.getenv("VERCEL_ENV", "").strip().lower() == "production":
        return False
    if os.getenv("RAILWAY_ENVIRONMENT", "").strip().lower() == "production":
        return False
    if os.getenv("RENDER", "").strip().lower() == "true":
        if os.getenv("IS_PULL_REQUEST", "").strip().lower() == "true":
            return True
        return False

    return True


def get_cors_config() -> dict:
    """
    CORS設定を返す。

    Returns:
        dict: CORSのパラメータ
    """
    return {
        'supports_credentials': True,
        'origins': [
            'https://medicine-recommend-system.onrender.com',
            'http://localhost:5000',
            'http://127.0.0.1:5000',
        ],
        'allow_headers': ['Content-Type', 'Authorization'],
        'methods': ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    }


def get_session_config() -> dict:
    """
    セッション設定を返す。
    is_development_runtime()（APP_ENV・ホスティングの慣例変数）と
    SESSION_COOKIE_SECURE により自動調整される。

    Returns:
        dict: Cookie 設定に利用するセッション関連の辞書
    """
    is_prod = not is_development_runtime()
    secure_override = os.getenv('SESSION_COOKIE_SECURE')
    if secure_override is not None:
        secure_flag = secure_override.lower() == 'true'
    else:
        secure_flag = is_prod
    samesite_value = 'None' if secure_flag else 'Lax'

    return {
        'SESSION_PERMANENT': False,
        'SESSION_TYPE': 'filesystem',
        'SESSION_COOKIE_SECURE': secure_flag,
        'SESSION_COOKIE_SAMESITE': samesite_value,
        'SESSION_COOKIE_HTTPONLY': False,
        'SESSION_COOKIE_DOMAIN': None,
    }
