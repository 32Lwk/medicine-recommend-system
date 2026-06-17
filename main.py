import importlib
import json
import logging
import math
import os
import re
from contextlib import asynccontextmanager
from pathlib import Path
import random
import time
import traceback
from datetime import datetime
from urllib.parse import unquote
from xml.sax.saxutils import escape

import httpx
import pytz
from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response as StarletteResponse, StreamingResponse

from config.app_config import (
    configure_logging,
    get_cors_config,
    get_session_config,
    is_development_runtime,
    load_env,
)
from config.settings import SESSION_COOKIE_MAX_AGE
from config.ui_config import (
    UI_VARIANT_COOKIE,
    UI_VARIANT_QUERY,
    resolve_ui_variant,
    ui_variant_cookie_max_age,
)
from src.core.season_manager import get_current_season, get_particle_profile, get_season_images
from src.handlers.chat_handler import handle_chat_post
from src.utils.chat_http_context import ChatClientInfo
from src.services.database import get_database, init_database, log_database_startup_summary
from src.services.session_manager import (
    clear_sessions_fallback,
    cleanup_old_sessions,
    get_admin_mode,
    get_admin_sessions,
    get_ai_auto_reply,
    get_all_sessions_from_db,
    get_manual_reply_message,
    get_manual_reply_queue,
    get_next_user_number,
    get_session_from_db,
    maybe_persist_session_activity,
    merge_session_messages,
    normalize_session_messages,
    persist_session_from_chat_state,
    ensure_session_persisted,
    purge_empty_sessions_on_startup,
    delete_session_by_id,
    is_session_recently_deleted,
    mark_session_deleted,
    get_manual_reply_session_ids,
    get_cleanup_exclude_session_ids,
    save_session_to_db,
    set_admin_mode,
    set_ai_auto_reply,
    set_manual_reply_message,
    set_manual_reply_queue,
)
from src.utils.performance_monitor import get_global_monitor
from src.utils.request_safe_session import RequestSafeSession
from src.utils.debug_logger import performance_stats, network_logs, add_network_log
import src.content.about_i18n as about_i18n_module
from src.content.about_i18n import (
    VALID_LANGS,
    about_lang_switch_rows,
    about_nav_entries,
    about_shell_labels,
    about_subpage_links,
    build_tech_diagram,
    get_about_bundle,
    normalize_query_lang,
)
from src.content.about_modal_html import get_mirror_html
from src.services.analytics import log_access_analytics

configure_logging()
load_env()
logger = logging.getLogger(__name__)


def _compute_cookie_settings() -> dict:
    cfg = get_session_config()
    # config keys -> Starlette cookie options
    return {
        "secure": bool(cfg.get("SESSION_COOKIE_SECURE", False)),
        "samesite": cfg.get("SESSION_COOKIE_SAMESITE", "lax"),
        "httponly": bool(cfg.get("SESSION_COOKIE_HTTPONLY", False)),
        "max_age": SESSION_COOKIE_MAX_AGE,
        "path": "/",
    }


COOKIE_NAME_SID = os.getenv("SID_COOKIE_NAME", "sid")
COOKIE_SETTINGS = _compute_cookie_settings()


async def _read_json_dict(request: Request) -> tuple[dict | None, JSONResponse | None]:
    """POST JSON を dict として読み取る。失敗時は呼び出し側が JSONResponse を返す。"""
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return None, JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(data, dict):
        return None, JSONResponse({"error": "Invalid payload"}, status_code=400)
    return data, None


def _clean_nan(obj):
    """NaN/Infinity を JSON 互換にする（管理画面 medicine_chat 互換）。"""
    if isinstance(obj, dict):
        return {k: _clean_nan(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_clean_nan(item) for item in obj]
    if isinstance(obj, float) and (math.isnan(obj) or math.isinf(obj)):
        return None
    return obj


async def get_sid(request: Request, response: Response) -> str:
    sid = request.cookies.get(COOKIE_NAME_SID)
    if sid:
        return sid

    # 既存実装（main_routes.index）に近い生成（microsec + random）
    sid = str(int(time.time() * 1000000)) + str(random.randint(100000, 999999))
    response.set_cookie(COOKIE_NAME_SID, sid, **COOKIE_SETTINGS)
    return sid


def _get_decoration_images(session_like: dict, version: str):
    try:
        jst = pytz.timezone("Asia/Tokyo")
        current_date = datetime.now(jst)
        season_type = get_current_season(current_date)
        year = current_date.year
        decoration_images = []
        if season_type:
            decoration_images = get_season_images(season_type, year, session_like)
        return decoration_images, version
    except Exception:
        return [], version


def _particle_profile_json() -> str:
    try:
        jst = pytz.timezone("Asia/Tokyo")
        now = datetime.now(jst)
        st = get_current_season(now)
        return json.dumps(get_particle_profile(st, now), ensure_ascii=False)
    except Exception:
        jst = pytz.timezone("Asia/Tokyo")
        return json.dumps(get_particle_profile(None, datetime.now(jst)), ensure_ascii=False)


@asynccontextmanager
async def _app_lifespan(app: FastAPI):
    try:
        init_database()
        from src.services.session_manager import is_db_persist_enabled

        is_db_persist_enabled()
        log_database_startup_summary()
        try:
            purged = purge_empty_sessions_on_startup()
            if purged:
                logger.info("Startup empty-session purge: removed %s rows", purged)
        except Exception as purge_err:
            logger.warning("Startup empty-session purge skipped: %s", purge_err)
    except Exception as e:
        logger.warning(
            "⚠️ Database startup unexpected error: %s. Feedback features will be disabled.",
            e,
        )

    async with httpx.AsyncClient(timeout=30.0) as line_http_client:
        from src.handlers.line import line_reply

        line_reply.set_http_client(line_http_client)
        yield
        line_reply.set_http_client(None)


app = FastAPI(redirect_slashes=False, lifespan=_app_lifespan)
security_basic = HTTPBasic(auto_error=False)

# CORS
cors_cfg = get_cors_config()
allow_origins = cors_cfg.get("origins", [])
allow_methods = cors_cfg.get("methods", ["GET", "POST", "PUT", "DELETE", "OPTIONS"])
allow_headers = cors_cfg.get("allow_headers", ["Content-Type", "Authorization"])
allow_credentials = bool(cors_cfg.get("supports_credentials", False))
app.add_middleware(
    CORSMiddleware,
    allow_origins=allow_origins,
    allow_methods=allow_methods,
    allow_headers=allow_headers,
    allow_credentials=allow_credentials,
)

# Static
app.mount("/static", StaticFiles(directory="static"), name="static")

_FAVICON_PATH = Path(__file__).resolve().parent / "static" / "favicon.ico.png"

templates = Jinja2Templates(directory="templates")

_PLACEHOLDER_APP_VERSION = re.compile(
    r"^\s*\{\{\s*version\s*\}\}\s*$",
    re.IGNORECASE,
)


def _normalized_app_version_env() -> str | None:
    """APP_VERSION が未設定・空・Jinja 未展開っぽい値なら None（呼び出し側でフォールバック）。"""
    raw = os.getenv("APP_VERSION")
    if raw is None:
        return None
    s = raw.strip()
    if not s:
        return None
    # クエリ文字列を誤ってコピーした場合（例: %7B%7B%20version%20%7D%7D）
    if "%" in s and ("%7b" in s.lower() or "%7d" in s.lower()):
        try:
            dec = unquote(s)
            if dec.strip():
                s = dec.strip()
        except Exception:
            pass
    if _PLACEHOLDER_APP_VERSION.match(s) or "{{" in s:
        return None
    return s


def _compat_url_for(endpoint: str, **values) -> str:
    # templates/*.html は Flask 互換の url_for('static', filename=...) を使用している。
    if endpoint == "static":
        filename = values.get("filename") or values.get("path") or ""
        if filename.startswith("/"):
            filename = filename[1:]
        return f"/static/{filename}"
    raise KeyError(f"Unsupported url_for endpoint: {endpoint}")


templates.env.globals["url_for"] = _compat_url_for


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    """404 は index.html を返す。それ以外は JSON。"""
    if exc.status_code == 404:
        logger.warning("⚠️ 404 Not Found: %s", request.url)
        sid = request.cookies.get(COOKIE_NAME_SID) or ""
        return _render_index(request, sid, app_base_path="", status_code=404)
    detail = exc.detail
    if not isinstance(detail, (dict, list)):
        detail = str(detail)
    return JSONResponse({"detail": detail}, status_code=exc.status_code)


@app.exception_handler(RequestValidationError)
async def _validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse({"detail": exc.errors()}, status_code=422)


@app.exception_handler(Exception)
async def _unhandled_exception_handler(request: Request, exc: Exception):
    if isinstance(exc, StarletteHTTPException):
        return await _http_exception_handler(request, exc)
    error_type = type(exc).__name__
    error_message = str(exc)
    stack_trace_str = traceback.format_exc()
    logger.error("❌ 500 Internal Server Error: %s", error_message)
    logger.error("❌ エラータイプ: %s", error_type)
    logger.error("❌ トレースバック:\n%s", stack_trace_str)

    ct = request.headers.get("content-type", "") or ""
    wants_json = request.method == "POST" or ct.startswith("application/json")

    if not os.getenv("OPENAI_API_KEY"):
        logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません！")
        error_msg = "⚠️ OpenAI APIキーが設定されていません。Renderの環境変数を確認してください。"
    else:
        error_msg = "申し訳ございません。システムエラーが発生しました。管理者に連絡してください。"

    try:
        from src.utils.structured_logger import log_error_detail

        log_error_detail(
            session_id=request.cookies.get(COOKIE_NAME_SID),
            error_type=error_type,
            error_message=error_message,
            stack_trace=stack_trace_str,
            user_input=None,
            system_state={},
            user_display_message=error_msg,
            conversation_history=None,
        )
    except Exception as log_err:
        logger.warning("エラーログ記録エラー: %s", log_err)

    if wants_json:
        return JSONResponse(
            {
                "error": True,
                "response": error_msg,
                "error_type": error_type if is_development_runtime() else None,
            },
            status_code=500,
        )
    return HTMLResponse(f"<h1>エラー</h1><p>{error_msg}</p>", status_code=500)


def _render_index(request: Request, sid: str, app_base_path: str, status_code: int = 200) -> HTMLResponse:
    # VERSION は毎プロセスで固定（キャッシュバスティング用）
    nv = _normalized_app_version_env()
    version = nv if nv is not None else str(int(time.time()))
    session_like = {"_id": sid} if sid else {}
    decoration_images, image_version = _get_decoration_images(session_like, version)
    particle_profile_json = _particle_profile_json()
    # 開発環境かどうか（config.app_config.is_development_runtime をテンプレート data-env に反映）
    is_dev_env = is_development_runtime()
    query_ui = request.query_params.get(UI_VARIANT_QUERY)
    cookie_ui = request.cookies.get(UI_VARIANT_COOKIE)
    ui_variant = resolve_ui_variant(query_ui=query_ui, cookie_ui=cookie_ui)
    runtime_client_config_json = json.dumps(
        {"isDevelopment": bool(is_dev_env), "uiVariant": ui_variant}
    )

    response = templates.TemplateResponse(
        request,
        "index.html",
        {
            "messages": [],
            "version": version,
            "username": "Unknown",
            "decoration_images": decoration_images,
            "image_version": image_version,
            "app_base_path": app_base_path,
            "particle_profile_json": particle_profile_json,
            "is_dev_env": is_dev_env,
            "runtime_client_config_json": runtime_client_config_json,
            "ui_variant": ui_variant,
        },
        status_code=status_code,
    )
    if query_ui is not None and str(query_ui).strip():
        response.set_cookie(
            UI_VARIANT_COOKIE,
            ui_variant,
            max_age=ui_variant_cookie_max_age(),
            httponly=False,
            samesite="lax",
        )
    return response


def _public_chat_root_url(request: Request) -> str:
    raw = os.getenv("PUBLIC_SITE_URL")
    if raw and str(raw).strip():
        return str(raw).strip().rstrip("/")
    return str(request.base_url).rstrip("/")


def _about_i18n_for_request():
    """開発時: uvicorn reload 無効でも /about の i18n・構成図を最新化する。"""
    if is_development_runtime():
        importlib.reload(about_i18n_module)
    return about_i18n_module


def _jinja_build_tech_diagram(lang: str):
    return _about_i18n_for_request().build_tech_diagram(lang)


templates.env.globals["build_tech_diagram"] = _jinja_build_tech_diagram


def _resolve_about_lang(request: Request, sid: str) -> str:
    q = normalize_query_lang(request.query_params.get("lang"))
    if q:
        return q
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            uil = session_data.get("ui_language")
            if uil in VALID_LANGS:
                return uil
    return "ja"


def _render_about_page(
    request: Request,
    page_id: str,
    app_base_path: str,
    sid: str,
    template_name: str,
) -> HTMLResponse:
    i18n = _about_i18n_for_request()
    lang = _resolve_about_lang(request, sid)
    shell = i18n.about_shell_labels(lang, app_base_path)
    index_bundle = i18n.get_about_bundle("index", lang)
    cta_aria = (index_bundle.get("cta_aria_label") or "").strip()

    user_agent = request.headers.get("user-agent", "") or ""
    client_ip = request.client.host if request.client else ""
    try:
        log_access_analytics(
            sid or "",
            user_agent,
            client_ip,
            0.0,
            {
                "access_kind": "about_get",
                "page": page_id,
                "path": request.url.path,
                "ui_language": lang,
                "query_lang": request.query_params.get("lang"),
            },
        )
    except Exception as ex:
        logger.warning("about page analytics log failed: %s", ex)

    bundle = dict(i18n.get_about_bundle(page_id, lang))
    if page_id == "index":
        # Always use full index bundle + canonical hero (never medicine_recommended on /about).
        bundle = dict(i18n.get_about_bundle("index", lang))
        bundle["hero_image"] = "img/about/generated/hero-pharmacy-chat.png"
        if not (bundle.get("hero_alt") or "").strip():
            bundle["hero_alt"] = i18n.get_about_bundle("index", "ja")["hero_alt"]
        bundle["tech_diagram"] = i18n.build_tech_diagram(lang)
    mirrored = get_mirror_html(page_id, lang, app_base_path or "")
    if mirrored is not None:
        bundle["body_html_safe"] = mirrored

    chat_href = _public_chat_root_url(request) + "/"
    nv = _normalized_app_version_env()
    version = nv if nv is not None else str(int(time.time()))

    ctx: dict = {
        "lang": lang,
        "page_id": page_id,
        "nav_entries": i18n.about_nav_entries(page_id, lang, app_base_path),
        "lang_switch": i18n.about_lang_switch_rows(),
        "chat_href": chat_href,
        "version": version,
        **shell,
        **bundle,
        "cta_aria_label": cta_aria,
        "cta_visible_text": shell["cta_visible_text"],
        "cta_footer_note": shell.get("cta_footer_note") or "",
    }
    if page_id == "index":
        ctx["subpage_links"] = i18n.about_subpage_links(lang, app_base_path)
    return templates.TemplateResponse(request, template_name, ctx)


@app.get("/", response_class=HTMLResponse)
def get_root(request: Request, response: Response, sid: str = Depends(get_sid)):
    return _render_index(request, sid, app_base_path="")


@app.get("/test/", response_class=HTMLResponse)
def get_test_root(request: Request, response: Response, sid: str = Depends(get_sid)):
    return _render_index(request, sid, app_base_path="/test")


@app.get("/about", response_class=HTMLResponse)
def get_about(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "index", "", sid, "about/index.html")


@app.get("/about/info", response_class=HTMLResponse)
def get_about_info(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "info", "", sid, "about/subpage.html")


@app.get("/about/privacy", response_class=HTMLResponse)
def get_about_privacy(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "privacy", "", sid, "about/subpage.html")


@app.get("/about/terms", response_class=HTMLResponse)
def get_about_terms(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "terms", "", sid, "about/subpage.html")


@app.get("/about/policies", response_class=HTMLResponse)
def get_about_policies(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "policies", "", sid, "about/subpage.html")


@app.get("/about/usage", response_class=HTMLResponse)
def get_about_usage(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "usage", "", sid, "about/subpage.html")


@app.get("/about/faq", response_class=HTMLResponse)
def get_about_faq(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "faq", "", sid, "about/subpage.html")


@app.get("/about/consultation", response_class=HTMLResponse)
def get_about_consultation(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "consultation", "", sid, "about/subpage.html")


@app.get("/test/about", response_class=HTMLResponse)
def get_test_about(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "index", "/test", sid, "about/index.html")


@app.get("/test/about/info", response_class=HTMLResponse)
def get_test_about_info(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "info", "/test", sid, "about/subpage.html")


@app.get("/test/about/privacy", response_class=HTMLResponse)
def get_test_about_privacy(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "privacy", "/test", sid, "about/subpage.html")


@app.get("/test/about/terms", response_class=HTMLResponse)
def get_test_about_terms(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "terms", "/test", sid, "about/subpage.html")


@app.get("/test/about/policies", response_class=HTMLResponse)
def get_test_about_policies(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "policies", "/test", sid, "about/subpage.html")


@app.get("/test/about/usage", response_class=HTMLResponse)
def get_test_about_usage(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "usage", "/test", sid, "about/subpage.html")


@app.get("/test/about/faq", response_class=HTMLResponse)
def get_test_about_faq(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "faq", "/test", sid, "about/subpage.html")


@app.get("/test/about/consultation", response_class=HTMLResponse)
def get_test_about_consultation(request: Request, sid: str = Depends(get_sid)):
    return _render_about_page(request, "consultation", "/test", sid, "about/subpage.html")


@app.get("/favicon.ico")
def favicon():
    if not _FAVICON_PATH.is_file():
        return StarletteResponse(status_code=204)
    return FileResponse(_FAVICON_PATH, media_type="image/png")


@app.get("/sitemap.xml")
def sitemap():
    # Canonical paths only (?lang は含めない). hreflang / 言語別 URL は別スコープ。
    base = (os.getenv("PUBLIC_SITE_URL") or "https://medicine.yutok.dev").rstrip("/")
    esc = {'"': "&quot;", "'": "&apos;"}
    paths_priority = [
        ("/", "1.0"),
        ("/about", "0.75"),
        ("/about/info", "0.65"),
        ("/about/usage", "0.65"),
        ("/about/faq", "0.65"),
        ("/about/policies", "0.65"),
        ("/about/terms", "0.6"),
        ("/about/privacy", "0.6"),
        ("/about/consultation", "0.65"),
    ]
    chunks = [
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>",
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    for path, priority in paths_priority:
        loc_raw = f"{base}/" if path == "/" else f"{base}{path}"
        loc = escape(loc_raw, esc)
        chunks.append(
            f"<url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>{priority}</priority></url>"
        )
    chunks.append("</urlset>")
    body = "".join(chunks)
    return StarletteResponse(content=body, media_type="application/xml; charset=utf-8")


def _prime_safe_session_for_chat(safe_session: RequestSafeSession, sid: str, request: Request):
    """
    旧実装に近い初期化を FastAPI 側で再現し、
    既存の chat_handler を互換利用できるようにする。
    """
    safe_session.setdefault("messages", [])
    safe_session.setdefault(
        "user_attributes",
        {
            "age": None,
            "gender": None,
            "pregnant": None,
            "breastfeeding": None,
            "current_medications": [],
            "allergies": [],
            "medical_history": [],
            "symptom_duration_days": None,
            "other_info": None,
        },
    )

    if sid:
        safe_session["_id"] = sid

    query_ui = request.query_params.get(UI_VARIANT_QUERY)
    cookie_ui = request.cookies.get(UI_VARIANT_COOKIE)
    safe_session["ui_variant"] = resolve_ui_variant(query_ui=query_ui, cookie_ui=cookie_ui)

    if "username" not in safe_session:
        safe_session["username"] = f"ユーザー{get_next_user_number()}"

    # DBがあればDB優先で復元
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            safe_session["messages"] = (session_data.get("messages") or []).copy()
            db_attrs = session_data.get("user_attributes") or {}
            if db_attrs:
                current_attrs = safe_session.get("user_attributes", {}) or {}
                safe_session["user_attributes"] = {**current_attrs, **db_attrs}


def _post_chat_json_response(request: Request, message: str, sid: str) -> JSONResponse:
    from src.core.language_utils import update_session_language_from_message
    from src.services.processing_status import (
        clear_processing_status,
        mark_processing_step,
        set_processing_language,
    )

    client_info = ChatClientInfo.from_starlette_request(request)
    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()

    safe_session = RequestSafeSession()
    _prime_safe_session_for_chat(safe_session, sid, request)

    if sid and (message or "").strip():
        set_processing_language(sid, update_session_language_from_message(safe_session, (message or "").strip()))
        mark_processing_step(sid, "validate")

    try:
        body, status_code = handle_chat_post(safe_session, client_info, message, sid, monitor)
        if not isinstance(body, dict) or not isinstance(status_code, int):
            body = {"error": True, "response": "サーバーから予期しない形式のレスポンスが返されました"}
            status_code = 500
        return JSONResponse(content=body, status_code=status_code)
    finally:
        if sid:
            try:
                persist_session_from_chat_state(sid, safe_session, request)
            except Exception as e:
                logger.warning("⚠️ チャットセッションの永続化に失敗: %s", e)
            clear_processing_status(sid)


@app.post("/", response_class=JSONResponse)
def post_root_chat(
    request: Request,
    response: Response,
    message: str = Form(...),
    sid: str = Depends(get_sid),
):
    return _post_chat_json_response(request, message, sid)


@app.post("/test/", response_class=JSONResponse)
def post_test_root_chat(
    request: Request,
    response: Response,
    message: str = Form(...),
    sid: str = Depends(get_sid),
):
    return _post_chat_json_response(request, message, sid)


@app.post("/api/chat/stream")
async def post_chat_stream(
    request: Request,
    message: str = Form(...),
    sid: str = Depends(get_sid),
):
    """SSE チャット（advice_delta / cards をリアルタイム配信）"""
    from src.handlers.chat_stream import stream_chat_events

    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()
    return StreamingResponse(
        stream_chat_events(request, message, sid, monitor),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/clear")
def clear_chat(request: Request, response: Response, sid: str = Depends(get_sid)):
    if sid:
        try:
            from src.services.sse_emit import clear_session_stream_state

            clear_session_stream_state(sid)
        except Exception:
            pass
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = []
            save_session_to_db(sid, session_data)
    return Response(status_code=204)


@app.post("/test/clear")
def clear_chat_test(request: Request, response: Response, sid: str = Depends(get_sid)):
    return clear_chat(request, response, sid)


@app.post("/new_session")
async def new_session(request: Request, response: Response):
    # 新規SIDを発行してcookieを書き換える（旧セッションは削除して再利用しない）
    old_sid = request.cookies.get(COOKIE_NAME_SID)
    if old_sid:
        mark_session_deleted(old_sid)
        try:
            from src.services.sse_emit import clear_session_stream_state

            clear_session_stream_state(old_sid)
        except Exception:
            pass
        try:
            delete_session_by_id(old_sid)
        except Exception:
            pass
    sid = str(int(time.time() * 1000000)) + str(random.randint(100000, 999999))
    response.set_cookie(COOKIE_NAME_SID, sid, **COOKIE_SETTINGS)
    username = f"ユーザー{get_next_user_number()}"
    ensure_session_persisted(
        sid,
        {
            "messages": [],
            "username": username,
            "user_attributes": {
                "age": None,
                "gender": None,
                "pregnant": None,
                "breastfeeding": None,
                "current_medications": [],
                "allergies": [],
                "medical_history": [],
                "symptom_duration_days": None,
                "other_info": None,
                "diagnosis_session_active": False,
                "diagnosis_block_types": [],
            },
            "session_active": False,
        },
        request,
    )

    return {"message": "新しいセッションを開始しました", "username": username, "session_id": sid}


@app.post("/test/new_session")
def new_session_test(request: Request, response: Response):
    return new_session(request, response)


@app.get("/resume/{token}")
async def resume_from_line(request: Request, token: str):
    """LINE ワンタイムトークンから Web セッションへフル引き継ぎ。"""
    from src.handlers.line.line_web_handoff import create_web_session_from_handoff, redeem_handoff_token

    snapshot = redeem_handoff_token(token)
    if not snapshot:
        return HTMLResponse(
            "<h1>リンクを利用できません</h1><p>有効期限切れ、または既に使用済みです。</p>",
            status_code=410,
        )
    sid = create_web_session_from_handoff(snapshot, request=request)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(COOKIE_NAME_SID, sid, **COOKIE_SETTINGS)
    return response


@app.post("/api/slow-request-notify")
async def api_slow_request_notify(
    request: Request,
    sid: str = Depends(get_sid),
):
    from src.services.slow_request_notify import notify_slow_request

    client_info = ChatClientInfo.from_starlette_request(request)
    last_msg = ""
    try:
        if request.headers.get("content-type", "").startswith("application/json"):
            body = await request.json()
            if isinstance(body, dict):
                last_msg = (body.get("last_user_message") or body.get("message") or "").strip()
    except Exception:
        pass
    if not last_msg:
        last_msg = request.query_params.get("message", "")
    notify_slow_request(
        sid,
        client_ip=client_info.client_ip,
        user_agent=client_info.user_agent,
        last_user_message=last_msg,
    )
    return {"status": "ok"}


@app.get("/api/processing-status")
def api_processing_status_get(
    request: Request,
    session_id: str | None = None,
    sid: str = Depends(get_sid),
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    from src.services.processing_status import get_processing_status

    target_sid = sid
    if session_id:
        if not _require_admin(request, creds):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        target_sid = session_id
    return get_processing_status(target_sid)


@app.get("/api/sessions")
async def api_sessions_get(
    request: Request,
    response: Response,
    sid: str = Depends(get_sid),
):
    session_data = get_session_from_db(sid)
    if session_data:
        session_data["last_activity"] = datetime.now()
        maybe_persist_session_activity(sid, session_data)
        messages = normalize_session_messages(session_data.get("messages", []) or [])
    else:
        messages = []

    user_attributes = (session_data or {}).get("user_attributes", {}) or {}

    latest_usage_notes = None
    for msg in reversed(messages):
        if msg.get("type") == "bot":
            diagnosis = msg.get("diagnosis")
            if isinstance(diagnosis, dict) and "usage_notes" in diagnosis:
                latest_usage_notes = diagnosis.get("usage_notes")
            if latest_usage_notes is None and "usage_notes" in msg:
                latest_usage_notes = msg.get("usage_notes")
            break

    return {
        "session_id": sid,
        "messages_count": len(messages),
        "last_activity": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "session_active": len(messages) > 0,
        "messages": messages,
        "user_attributes": user_attributes,
        "latest_usage_notes": latest_usage_notes,
        "medical_emergency_otc_locked": bool((session_data or {}).get("medical_emergency_otc_locked")),
        "otc_lock_released": bool((session_data or {}).get("otc_lock_released")),
        "store_incident_soft_banner": bool((session_data or {}).get("store_incident_soft_banner")),
        "emergency_subtype": (session_data or {}).get("emergency_subtype"),
    }


@app.patch("/api/sessions/activity")
async def api_sessions_activity(
    request: Request,
    sid: str = Depends(get_sid),
):
    """DB 行がある場合のみ last_activity を更新（空セッションは作成しない）。"""
    session_data = get_session_from_db(sid)
    if not session_data:
        return Response(status_code=204)
    session_data["last_activity"] = datetime.now()
    maybe_persist_session_activity(sid, session_data)
    return {"status": "ok", "session_id": sid}


@app.post("/api/chat/otc_unlock")
async def api_chat_otc_unlock(
    request: Request,
    sid: str = Depends(get_sid),
):
    """メディカル緊急後の OTC ハードロックを明示解除（ユーザーの自己判断）。"""
    session_data = get_session_from_db(sid) or {}
    if not session_data.get("medical_emergency_otc_locked"):
        return JSONResponse(
            content={"status": "ok", "otc_unlocked": False, "message": "ロックは有効ではありません"},
            status_code=200,
        )
    session_data["otc_lock_released"] = True
    session_data["medical_emergency_otc_unlocked_at"] = datetime.now().isoformat()
    save_session_to_db(sid, session_data)
    return JSONResponse(
        content={
            "status": "ok",
            "otc_unlocked": True,
            "message": "市販薬の相談を再開できます。緊急でないことをご確認のうえご利用ください。",
        },
        status_code=200,
    )


@app.post("/api/chat/store_incident_ack")
async def api_chat_store_incident_ack(
    request: Request,
    sid: str = Depends(get_sid),
):
    """店舗インシデント後のソフトバナーを閉じ、OTC 相談へ進む意思を記録。"""
    session_data = get_session_from_db(sid) or {}
    session_data["store_incident_soft_banner"] = False
    session_data["store_incident_otc_opt_in"] = True
    save_session_to_db(sid, session_data)
    return JSONResponse(content={"status": "ok", "banner_dismissed": True}, status_code=200)


@app.post("/api/sessions/restore")
async def api_sessions_restore(
    request: Request,
    response: Response,
    sid: str = Depends(get_sid),
):
    """タブ内キャッシュからサーバー側セッションを復元（メモリ喪失・再起動後など）。"""
    data, err = await _read_json_dict(request)
    if err:
        return err
    client_messages = data.get("messages")
    if not isinstance(client_messages, list):
        return JSONResponse({"error": "messages must be a list"}, status_code=400)

    if is_session_recently_deleted(sid):
        return {
            "status": "ok",
            "session_id": sid,
            "messages_count": 0,
            "restored": False,
            "messages": [],
            "rejected": "session_deleted",
        }

    session_data = get_session_from_db(sid) or {
        "session_id": sid,
        "messages": [],
        "user_attributes": {},
    }

    server_messages = session_data.get("messages") or []
    if server_messages:
        return {
            "status": "ok",
            "session_id": sid,
            "messages_count": len(server_messages),
            "restored": False,
            "messages": server_messages,
        }

    merged = merge_session_messages([], client_messages)
    if not merged:
        return {
            "status": "ok",
            "session_id": sid,
            "messages_count": 0,
            "restored": False,
            "messages": [],
        }
    ensure_session_persisted(
        sid,
        {
            "messages": merged,
            "session_active": True,
            "user_attributes": session_data.get("user_attributes") or {},
        },
        request,
    )
    session_data = get_session_from_db(sid) or session_data
    session_data["messages"] = merged

    return {
        "status": "ok",
        "session_id": sid,
        "messages_count": len(merged),
        "restored": len(merged) > 0,
        "messages": merged,
    }


@app.post("/api/sessions")
async def api_sessions_post(
    request: Request,
    response: Response,
    sid: str = Depends(get_sid),
):
    data, err = await _read_json_dict(request)
    if err:
        return err
    user_attributes = data.get("user_attributes", {}) if isinstance(data, dict) else {}
    ensure_session_persisted(
        sid,
        {
            "user_attributes": user_attributes,
            "session_active": True,
        },
        request,
    )
    return {"status": "ok", "message": "ユーザー情報を保存しました"}

@app.get("/line/webhook/status")
async def line_webhook_status():
    """LINE Webhook 設定状態（秘密値は含まない）。ローカル・GCP の環境確認用。"""
    from src.handlers.line.line_webhook import line_webhook_status as _status

    return _status()


@app.post("/line/webhook")
async def line_webhook(request: Request):
    """LINE Messaging API Webhook（署名検証のみ・Reply 未実装）。"""
    from src.handlers.line.line_webhook import handle_line_webhook

    return await handle_line_webhook(request)


@app.post("/api/submit_feedback")
async def submit_feedback(
    request: Request,
    response: Response,
    sid: str = Depends(get_sid),
):
    try:
        data = await request.json()
    except json.JSONDecodeError:
        return JSONResponse({"error": "Invalid JSON"}, status_code=400)
    if not isinstance(data, dict):
        return JSONResponse({"error": "Invalid payload"}, status_code=400)

    required_fields = ["report_type", "user_message", "ai_response"]
    for field in required_fields:
        if field not in data:
            return JSONResponse({"error": f"Missing required field: {field}"}, status_code=400)

    session_data = get_session_from_db(sid) or {}
    username = session_data.get("username") or "Unknown"
    negative_reason = data.get("negative_reason")
    if negative_reason is not None:
        negative_reason = str(negative_reason).strip()[:64] or None

    from src.services.feedback_submit import FeedbackSubmitError, submit_feedback_record

    try:
        return submit_feedback_record(
            report_type=data["report_type"],
            session_id=sid or "",
            username=username,
            user_message=data["user_message"],
            ai_response=data["ai_response"],
            security_score=data.get("security_score"),
            feedback_text=data.get("feedback_text", "") or "",
            is_google_form=bool(data.get("is_google_form", False)),
            negative_reason=negative_reason,
            dedupe=True,
        )
    except FeedbackSubmitError as exc:
        return JSONResponse({"error": str(exc)}, status_code=exc.status_code)


@app.get("/api/get_feedback_reports")
def get_feedback_reports(limit: int = 100, unresolved_only: bool = False):
    db = get_database()
    if db and (db.connection or db.connection_pool):
        reports = db.get_feedback_reports(limit=limit, unresolved_only=unresolved_only)
        return {"reports": reports}
    if is_development_runtime():
        from src.services.feedback_store import list_feedback_dev

        return {
            "reports": list_feedback_dev(limit=limit, unresolved_only=unresolved_only),
            "storage": "dev_fallback",
        }
    return JSONResponse({"error": "Database not available"}, status_code=500)


@app.post("/api/resolve_feedback/{feedback_id}")
def resolve_feedback(feedback_id: int):
    db = get_database()
    if db and (db.connection or db.connection_pool):
        if db.resolve_feedback(feedback_id):
            return {"status": "success"}
        return JSONResponse({"error": "Failed to resolve feedback"}, status_code=500)
    if is_development_runtime():
        from src.services.feedback_store import resolve_feedback_dev

        if resolve_feedback_dev(feedback_id):
            return {"status": "success", "storage": "dev_fallback"}
        return JSONResponse({"error": "Feedback not found"}, status_code=404)
    return JSONResponse({"error": "Database not available"}, status_code=500)


@app.post("/api/delete_feedback/{feedback_id}")
def delete_feedback(feedback_id: int):
    db = get_database()
    if db and (db.connection or db.connection_pool):
        if db.delete_feedback(feedback_id):
            return {"status": "success"}
        return JSONResponse({"error": "Failed to delete feedback"}, status_code=500)
    if is_development_runtime():
        from src.services.feedback_store import delete_feedback_dev

        if delete_feedback_dev(feedback_id):
            return {"status": "success", "storage": "dev_fallback"}
        return JSONResponse({"error": "Feedback not found"}, status_code=404)
    return JSONResponse({"error": "Database not available"}, status_code=500)


def _admin_unauthorized_response():
    return JSONResponse({"error": "Unauthorized"}, status_code=401)


def _require_admin(
    request: Request,
    credentials: HTTPBasicCredentials | None = None,
) -> bool:
    from src.services.admin_auth import (
        ADMIN_COOKIE_NAME,
        credentials_match,
        verify_admin_token,
    )

    if credentials and credentials_match(credentials.username, credentials.password):
        return True
    return verify_admin_token(request.cookies.get(ADMIN_COOKIE_NAME))


def _admin_json_guard(
    request: Request,
    creds: HTTPBasicCredentials | None = None,
):
    if not _require_admin(request, creds):
        return _admin_unauthorized_response()
    return None


def _set_admin_cookie(response: Response) -> None:
    from src.services.admin_auth import ADMIN_COOKIE_NAME, create_admin_token

    response.set_cookie(
        ADMIN_COOKIE_NAME,
        create_admin_token(),
        max_age=60 * 60 * 24 * 7,
        httponly=True,
        samesite=COOKIE_SETTINGS.get("samesite", "lax"),
        secure=bool(COOKIE_SETTINGS.get("secure", False)),
        path="/",
    )


def _clear_admin_cookie(response: Response) -> None:
    from src.services.admin_auth import ADMIN_COOKIE_NAME

    response.delete_cookie(ADMIN_COOKIE_NAME, path="/")


@app.get("/admin/login", response_class=HTMLResponse)
def admin_login_page(request: Request, creds: HTTPBasicCredentials | None = Depends(security_basic)):
    if _require_admin(request, creds):
        return RedirectResponse(url="/admin", status_code=302)
    return templates.TemplateResponse(request, "admin_login.html", {"error": None})


@app.post("/admin/login", response_class=HTMLResponse)
async def admin_login_post(
    request: Request,
    username: str = Form(""),
    password: str = Form(""),
):
    from src.services.admin_auth import credentials_match

    if credentials_match(username.strip(), password):
        response = RedirectResponse(url="/admin", status_code=302)
        _set_admin_cookie(response)
        return response
    return templates.TemplateResponse(
        request,
        "admin_login.html",
        {"error": "ユーザー名またはパスワードが正しくありません"},
        status_code=401,
    )


@app.get("/admin/logout")
def admin_logout():
    response = RedirectResponse(url="/admin/login", status_code=302)
    _clear_admin_cookie(response)
    return response


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, creds: HTTPBasicCredentials | None = Depends(security_basic)):
    if not _require_admin(request, creds):
        return RedirectResponse(url="/admin/login", status_code=302)
    return templates.TemplateResponse(request, "admin_chat.html", {})


def _session_row_for_admin(sess_id, info):
    from src.services.session_lifecycle import admin_messages_for_session
    from src.handlers.line.line_session import is_line_session_id

    detailed_diag = None
    if isinstance(info, dict):
        detailed_diag = info.get("detailed_diagnosis")
    if not detailed_diag:
        detailed_diag = get_admin_sessions().get(sess_id, {}).get("detailed_diagnosis")
    if isinstance(detailed_diag, dict) and "session_id" not in detailed_diag:
        try:
            detailed_diag = dict(detailed_diag)
            detailed_diag["session_id"] = sess_id
        except Exception:
            pass
    if not isinstance(info, dict):
        info = {}
    admin_msgs = admin_messages_for_session(info)
    live_count = len(info.get("messages", []) or [])
    archive_count = len(admin_msgs)
    msg_count = archive_count
    row = {
        "session_id": sess_id,
        "username": info.get("username", "Unknown"),
        "messages": admin_msgs,
        "messages_live": info.get("messages", []),
        "last_activity": info.get("last_activity", 0),
        "message_count": msg_count,
        "messages_count": msg_count,
        "messages_live_count": live_count,
        "message_archive_count": archive_count,
        "user_info": info.get("user_attributes", {}),
        "attributes": info.get("user_attributes", {}),
        "user_attributes": info.get("user_attributes", {}),
        "detailed_diagnosis": detailed_diag,
        "crisis_detected": bool(info.get("crisis_detected")),
        "line_profile": info.get("line_profile"),
        "line_profile_error": info.get("line_profile_error"),
        "lifecycle_log": info.get("lifecycle_log") or [],
        "is_line_session": is_line_session_id(str(sess_id)),
    }
    return row


def _list_admin_sessions(meaningful_only: bool = True):
    from src.handlers.line.line_session import is_line_session_id
    from src.services.session_lifecycle import ensure_line_session_archive

    queue_ids = get_manual_reply_session_ids()
    all_sessions = get_all_sessions_from_db()
    sessions_list = []
    for sess_id, info in all_sessions.items():
        if isinstance(info, dict) and is_line_session_id(str(sess_id)):
            if ensure_line_session_archive(info):
                save_session_to_db(sess_id, info)
        row = _session_row_for_admin(sess_id, info)
        if meaningful_only:
            has_messages = row["message_count"] > 0
            in_queue = str(sess_id) in queue_ids
            is_line = is_line_session_id(str(sess_id))
            if not has_messages and not in_queue and not is_line:
                continue
        sessions_list.append(row)
    return sessions_list


@app.get("/api/main_sessions")
def api_main_sessions(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    raw = request.query_params.get("meaningful_only", "1")
    meaningful_only = str(raw).strip().lower() not in ("0", "false", "no")
    cleanup_old_sessions(
        force=False,
        exclude_current_session=False,
        current_sid=None,
        skip_empty_sessions=not meaningful_only,
    )
    return {"sessions": _list_admin_sessions(meaningful_only=meaningful_only)}


@app.get("/api/main_session")
async def api_main_session(
    request: Request,
    session_id: str,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    if not session_id:
        return JSONResponse({"status": "error", "message": "session_id required"}, status_code=400)
    from src.handlers.line.line_session import is_line_session_id, normalize_line_session_id
    from src.handlers.line.line_profile import refresh_line_profile_by_session_id

    session_id = normalize_line_session_id(session_id) or session_id
    info = get_session_from_db(session_id)
    if not info and is_line_session_id(session_id):
        from src.handlers.line.line_session import user_id_from_line_sid

        uid = user_id_from_line_sid(session_id)
        info = {
            "session_id": session_id,
            "messages": [],
            "username": f"LINEユーザー{(uid or '????')[-6:]}",
        }
    elif not info:
        return JSONResponse({"status": "error", "message": "session not found"}, status_code=404)
    if is_line_session_id(session_id):
        from src.services.session_lifecycle import ensure_line_session_archive, merge_messages_into_archive

        if info.get("messages"):
            merge_messages_into_archive(info, info.get("messages") or [])
        ensure_line_session_archive(info)
        save_session_to_db(session_id, info)
        profile_result = await refresh_line_profile_by_session_id(session_id, force=True)
        if not profile_result.get("ok"):
            info["line_profile_error"] = profile_result.get("error")
        info = get_session_from_db(session_id) or info
        if not profile_result.get("ok"):
            info["line_profile_error"] = profile_result.get("error")
    return {"session": _session_row_for_admin(session_id, info)}


@app.post("/api/main_line_profile_refresh")
async def api_main_line_profile_refresh(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    data, err = await _read_json_dict(request)
    if err:
        return err
    session_id = data.get("session_id")
    if not session_id:
        return JSONResponse({"status": "error", "message": "session_id required"}, status_code=400)
    from src.handlers.line.line_profile import refresh_line_profile_by_session_id

    result = await refresh_line_profile_by_session_id(session_id, force=True)
    if not result.get("ok"):
        return JSONResponse({"status": "error", **result}, status_code=400)
    info = get_session_from_db(session_id) or {}
    return {"status": "success", "session": _session_row_for_admin(session_id, info)}


@app.get("/api/main_manual_reply_queue")
def api_main_manual_reply_queue(
    request: Request,
    priority_tag: str | None = None,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    from src.utils.admin_snippet import truncate_user_text

    queue = get_manual_reply_queue()
    enriched = []
    for item in queue:
        row = dict(item)
        msg = row.get("user_message") or ""
        row.setdefault("user_message_snippet", truncate_user_text(msg, "list"))
        row["user_message_detail"] = truncate_user_text(msg, "detail")
        if priority_tag and row.get("priority_tag") != priority_tag:
            continue
        enriched.append(row)
    return enriched


@app.post("/api/main_manual_reply_queue")
async def api_main_manual_reply_queue_post(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    data, err = await _read_json_dict(request)
    if err:
        return err
    action = data.get("action")
    session_id = data.get("session_id")
    queue = get_manual_reply_queue()

    if not action and data.get("reply_message"):
        action = "reply"

    if action == "remove" and session_id:
        queue = [q for q in queue if q.get("session_id") != session_id]
        set_manual_reply_queue(queue)
        return {"status": "success", "queue": get_manual_reply_queue()}

    if action == "acknowledge" and session_id:
        for item in queue:
            if item.get("session_id") != session_id:
                continue
            item["acknowledged"] = True
            ns = dict(item.get("notification_status") or {})
            ns["admin"] = "acknowledged"
            item["notification_status"] = ns
            break
        set_manual_reply_queue(queue)
        return {"status": "success", "queue": get_manual_reply_queue()}

    if action == "retry_email" and session_id:
        from src.services.emergency_notify import (
            build_notification_status,
            notify_emergency_detected,
        )

        target = next((q for q in queue if q.get("session_id") == session_id), None)
        if not target:
            return JSONResponse({"status": "error", "message": "キューにありません"}, status_code=404)
        email_status = notify_emergency_detected(
            session_id=session_id,
            user_message=target.get("user_message") or "",
            priority_tag=target.get("priority_tag") or "store_high",
            emergency_subtype=target.get("emergency_subtype") or "medical_self",
            emergency_type=target.get("emergency_type"),
            trace_id=target.get("trace_id"),
        )
        ns = dict(target.get("notification_status") or {})
        ns["email"] = email_status
        target["notification_status"] = build_notification_status(email_status)
        target["notification_status"]["admin"] = ns.get("admin", "pending")
        set_manual_reply_queue(queue)
        return {"status": "success", "email": email_status, "queue": get_manual_reply_queue()}

    if action == "reply":
        message = data.get("reply_message") or data.get("message")
        if session_id and message:
            from src.handlers.line.line_admin_manual_reply import apply_admin_manual_reply

            result = await apply_admin_manual_reply(session_id, message)
            if not result.get("ok"):
                err = result.get("error") or "無効なアクションです"
                status_code = 404 if err == "session not found" else 400
                return JSONResponse({"status": "error", "message": err}, status_code=status_code)
            queue = [q for q in queue if q.get("session_id") != session_id]
            set_manual_reply_queue(queue)
            payload = {
                "status": "success",
                "message": "メッセージを送信しました",
                "target_session_id": result.get("target_session_id"),
            }
            if result.get("line_pushed") is not None:
                payload["line_pushed"] = result["line_pushed"]
            if result.get("line_error"):
                payload["line_error"] = result["line_error"]
            return payload
        return JSONResponse({"status": "error", "message": "無効なアクションです"}, status_code=400)

    return JSONResponse({"status": "error", "message": "無効なアクションです"}, status_code=400)


@app.get("/api/main_ai_control")
def api_main_ai_control(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    return {
        "ai_auto_reply": get_ai_auto_reply(),
        "admin_mode": get_admin_mode(),
        "manual_reply_message": get_manual_reply_message(),
    }


@app.post("/api/main_ai_control")
async def api_main_ai_control_post(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    data, err = await _read_json_dict(request)
    if err:
        return err
    action = data.get("action")
    mode = data.get("mode")
    if mode == "on":
        mode = "auto"
    elif mode == "off":
        mode = "manual"

    if mode == "auto" or action == "enable":
        set_ai_auto_reply(True)
        set_admin_mode(False)
        message = "AI自動応答を有効化しました"
    elif mode == "manual" or action == "disable":
        set_ai_auto_reply(False)
        set_admin_mode(True)
        message = "AI自動応答を無効化しました"
    else:
        return JSONResponse({"error": "無効なパラメータです"}, status_code=400)

    return {
        "ai_auto_reply": get_ai_auto_reply(),
        "admin_mode": get_admin_mode(),
        "message": message,
        "manual_reply_message": get_manual_reply_message(),
    }


@app.get("/api/manual_reply_message")
def api_manual_reply_message_get():
    return {"message": get_manual_reply_message()}


@app.post("/api/manual_reply_message")
async def api_manual_reply_message_post(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    message = (data.get("message") or "").strip()
    if not message:
        return JSONResponse({"error": "メッセージが空です"}, status_code=400)
    set_manual_reply_message(message)
    saved = get_manual_reply_message() or message
    return {"message": "メッセージを保存しました", "manual_reply_message": saved}


@app.get("/api/status")
def api_status(sid: str = Depends(get_sid)):
    from src.core.medicine_logic import csv_load_status

    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "csv_load_status": {
            "success": csv_load_status.get("success", False),
            "encoding": csv_load_status.get("encoding"),
            "error": csv_load_status.get("error"),
            "row_count": csv_load_status.get("row_count", 0),
            "col_count": csv_load_status.get("col_count", 0),
            "columns": csv_load_status.get("columns", []),
            "path": str(csv_load_status.get("path")) if csv_load_status.get("path") is not None else None,
        },
        "session_active": bool(get_session_from_db(sid)) if sid else False,
        "message_count": len((get_session_from_db(sid) or {}).get("messages", []) or []) if sid else 0,
        "version": _normalized_app_version_env() or "0",
    }


@app.get("/api/performance")
def api_performance():
    return performance_stats


@app.get("/api/logs")
def api_logs():
    if not isinstance(network_logs, list):
        return []
    return network_logs


@app.post("/api/admin_mode")
def api_admin_mode():
    set_admin_mode(True)
    set_ai_auto_reply(False)
    return {
        "admin_mode": get_admin_mode(),
        "ai_auto_reply": get_ai_auto_reply(),
        "message": "管理者対応モードに切り替えました",
    }


@app.get("/api/ai_control")
def api_ai_control_get():
    return {
        "ai_auto_reply": get_ai_auto_reply(),
        "manual_reply_queue_count": len(get_manual_reply_queue()),
    }


@app.post("/api/ai_control")
async def api_ai_control_post(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    mode = data.get("mode")
    if mode in ["on", "off"]:
        set_ai_auto_reply(mode == "on")
        return {
            "ai_auto_reply": get_ai_auto_reply(),
            "message": f'AI自動応答を{"ON" if get_ai_auto_reply() else "OFF"}にしました',
        }
    return JSONResponse({"error": 'Invalid mode. Use "on" or "off"'}, status_code=400)


@app.get("/api/manual_reply_queue")
def api_manual_reply_queue_get():
    return get_manual_reply_queue()


@app.post("/api/manual_reply_queue")
async def api_manual_reply_queue_post(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    session_id = data.get("session_id")
    reply_message = data.get("reply_message")
    if not session_id or not reply_message:
        return JSONResponse({"error": "session_id and reply_message are required"}, status_code=400)

    queue = get_manual_reply_queue()
    queue = [q for q in queue if q.get("session_id") != session_id]
    set_manual_reply_queue(queue)

    target_session = get_session_from_db(session_id)
    if not target_session:
        return JSONResponse({"error": f"Session {session_id} not found"}, status_code=404)

    manual_reply_message_obj = {
        "type": "bot",
        "content": reply_message,
        "diagnosis": None,
        "manual_reply": True,
    }
    target_session.setdefault("messages", [])
    target_session["messages"].append(manual_reply_message_obj)
    target_session["last_activity"] = datetime.now()
    save_session_to_db(session_id, target_session)
    return {
        "message": "手動返信を送信しました",
        "remaining_queue": len(get_manual_reply_queue()),
        "target_session_id": session_id,
        "messages_count": len(target_session.get("messages", [])),
        "session_updated": True,
    }


@app.get("/api/all_sessions")
def api_all_sessions():
    result = []
    all_sessions = get_all_sessions_from_db()
    for sess_id, info in all_sessions.items():
        if not isinstance(info, dict):
            info = {}
        result.append(
            {
                "session_id": sess_id,
                "username": info.get("username", ""),
                "messages": info.get("messages", []),
                "messages_count": len(info.get("messages", []) or []),
            }
        )
    return result


@app.get("/api/session_stats")
def api_session_stats():
    from config.settings import MAX_SESSIONS, SESSION_TIMEOUT

    current_time = time.time()
    active_sessions = 0
    expired_sessions = 0
    used_user_numbers = set()
    session_details = []

    all_sessions = get_all_sessions_from_db()
    for sess_id, info in all_sessions.items():
        if not isinstance(info, dict):
            continue
        last_activity = info.get("last_activity", 0)
        if isinstance(last_activity, datetime):
            last_ts = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_ts = datetime.fromisoformat(last_activity.replace("Z", "+00:00")).timestamp()
            except Exception:
                last_ts = 0
        else:
            last_ts = float(last_activity or 0)

        if current_time - last_ts < SESSION_TIMEOUT:
            active_sessions += 1
            username = info.get("username", "")
            if isinstance(username, str) and username.startswith("ユーザー"):
                try:
                    used_user_numbers.add(int(username.replace("ユーザー", "")))
                except Exception:
                    pass
            session_details.append(
                {
                    "session_id": sess_id,
                    "username": username,
                    "client_ip": info.get("client_ip", ""),
                    "user_agent": (info.get("user_agent", "") or "")[:50] + "...",
                    "messages_count": len(info.get("messages", []) or []),
                    "last_activity": datetime.fromtimestamp(last_ts).strftime("%Y-%m-%d %H:%M:%S"),
                    "age_minutes": int((current_time - last_ts) / 60) if last_ts else 0,
                }
            )
        else:
            expired_sessions += 1

    return {
        "total_sessions": len(all_sessions),
        "active_sessions": active_sessions,
        "expired_sessions": expired_sessions,
        "max_sessions": MAX_SESSIONS,
        "session_timeout": SESSION_TIMEOUT,
        "current_user_counter": 0,
        "used_user_numbers": sorted(list(used_user_numbers)),
        "next_available_number": get_next_user_number(),
        "session_details": session_details,
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }


@app.get("/api/debug_manual_replies")
def api_debug_manual_replies():
    all_sessions = get_all_sessions_from_db()
    queue = get_manual_reply_queue()
    sessions_with_manual_replies = []
    for sess_id, info in all_sessions.items():
        if not isinstance(info, dict):
            continue
        manual_replies = [msg for msg in (info.get("messages", []) or []) if msg.get("manual_reply")]
        if manual_replies:
            sessions_with_manual_replies.append(
                {
                    "session_id": sess_id,
                    "username": info.get("username", ""),
                    "manual_replies_count": len(manual_replies),
                    "manual_replies": manual_replies,
                    "total_messages": len(info.get("messages", []) or []),
                }
            )
    return {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "total_sessions": len(all_sessions),
        "sessions_with_manual_replies": sessions_with_manual_replies,
        "manual_reply_queue": queue,
    }


@app.post("/api/set_language")
async def api_set_language(request: Request, sid: str = Depends(get_sid)):
    data, err = await _read_json_dict(request)
    if err:
        return err
    language = data.get("language", "ja")
    if language not in ["ja", "en", "ko", "zh"]:
        return JSONResponse({"error": "Invalid language code"}, status_code=400)
    if sid:
        session_data = get_session_from_db(sid) or {"session_id": sid}
        session_data["ui_language"] = language
        save_session_to_db(sid, session_data)
    return {"status": "success", "language": language, "message": f"Language set to {language}"}


@app.get("/api/user_attributes")
def api_user_attributes_get(sid: str = Depends(get_sid)):
    session_data = get_session_from_db(sid) or {}
    return session_data.get(
        "user_attributes",
        {
            "age": None,
            "gender": None,
            "pregnant": None,
            "breastfeeding": None,
            "current_medications": [],
            "allergies": [],
            "medical_history": [],
            "symptom_duration_days": None,
            "other_info": None,
        },
    )


@app.post("/api/user_attributes")
async def api_user_attributes_post(request: Request, sid: str = Depends(get_sid)):
    data, err = await _read_json_dict(request)
    if err:
        return err
    session_data = get_session_from_db(sid) or {"session_id": sid}
    session_data["user_attributes"] = {
        "age": data.get("age"),
        "gender": data.get("gender"),
        "pregnant": data.get("pregnant"),
        "breastfeeding": data.get("breastfeeding"),
        "current_medications": data.get("current_medications", []),
        "allergies": data.get("allergies", []),
        "medical_history": data.get("medical_history", []),
        "symptom_duration_days": data.get("symptom_duration_days"),
        "other_info": data.get("other_info"),
    }
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)
    return {"status": "success", "message": "ユーザー属性を保存しました"}


@app.post("/api/translate")
async def api_translate(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    text = data.get("text", "")
    target_language = data.get("target_language", "ja")
    if not text:
        return JSONResponse({"error": "No text provided"}, status_code=400)
    from src.core.medicine_logic import client

    translation_prompt = f"""
以下の医薬品関連情報を{target_language}に翻訳してください。医療専門用語は正確に翻訳し、医薬品名は適切に翻訳してください。

翻訳対象テキスト:
{text}

翻訳:
"""
    try:
        from src.core.llm_client import chat_completion_create

        resp = chat_completion_create(
            client,
            model_role="ask",
            path="main.translate",
            messages=[
                {
                    "role": "system",
                    "content": "You are a medical translator specializing in medicine recommendations. Translate accurately while maintaining medical terminology.",
                },
                {"role": "user", "content": translation_prompt},
            ],
            temperature=0.1,
            max_tokens=2000,
        )
        translated_text = resp.choices[0].message.content.strip()
        return {"translated_text": translated_text, "original_text": text, "target_language": target_language}
    except Exception:
        return JSONResponse({"error": "Translation failed"}, status_code=500)


@app.get("/admin/system_status")
def admin_system_status():
    from config.settings import SESSION_TIMEOUT

    all_sessions = get_all_sessions_from_db()
    current_time = time.time()
    active_sessions = 0
    for s in all_sessions.values():
        if not isinstance(s, dict):
            continue
        last_activity = s.get("last_activity", 0)
        if isinstance(last_activity, datetime):
            last_ts = last_activity.timestamp()
        elif isinstance(last_activity, str):
            try:
                last_ts = datetime.fromisoformat(last_activity.replace("Z", "+00:00")).timestamp()
            except Exception:
                last_ts = 0
        else:
            last_ts = float(last_activity or 0)
        if current_time - last_ts < SESSION_TIMEOUT:
            active_sessions += 1
    from src.core.medicine_logic import csv_load_status
    from src.services.database import get_database_status

    return {
        "status": "ok",
        "csv_load_status": csv_load_status,
        "total_sessions": len(all_sessions),
        "active_sessions": active_sessions,
        "manual_reply_queue": len(get_manual_reply_queue()),
        "ai_auto_reply": get_ai_auto_reply(),
        "admin_mode": get_admin_mode(),
        "performance_stats": performance_stats,
        "database": get_database_status(),
    }


@app.get("/admin/access_stats")
def admin_access_stats():
    from src.services.analytics import get_access_statistics

    return get_access_statistics()


@app.get("/admin/performance_stats")
def admin_performance_stats():
    from src.utils.performance_monitor import get_performance_statistics

    return get_performance_statistics()


@app.get("/admin/browser_distribution")
def admin_browser_distribution():
    from src.services.analytics import get_browser_distribution

    return get_browser_distribution()


@app.get("/admin/os_distribution")
def admin_os_distribution():
    from src.services.analytics import get_os_distribution

    return get_os_distribution()


@app.get("/admin/device_distribution")
def admin_device_distribution():
    from src.services.analytics import get_device_distribution

    return get_device_distribution()


@app.get("/admin/realtime_monitoring")
def admin_realtime_monitoring():
    monitor = get_global_monitor()
    metrics = monitor.get_metrics()
    all_sessions = get_all_sessions_from_db()
    return {
        "memory_usage_percent": metrics.get("memory_usage_percent", 0),
        "cpu_usage_percent": metrics.get("cpu_usage_percent", 0),
        "response_time_ms": metrics.get("response_time_ms", 0),
        "active_sessions": len(all_sessions),
        "api_calls": metrics.get("api_calls", 0),
        "cache_hit_rate": metrics.get("cache_hit_rate", 0),
    }


@app.get("/admin/export_monitoring_data")
def admin_export_monitoring_data():
    from src.services.analytics import get_access_statistics
    from src.utils.performance_monitor import get_performance_statistics

    return {
        "access_stats": get_access_statistics(),
        "performance_stats": get_performance_statistics(),
        "export_time": datetime.now().isoformat(),
    }


@app.get("/admin/llm_settings")
def admin_llm_settings_get(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    if not _require_admin(request, creds):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from src.services.budget_guard import ensure_llm_admin_defaults, get_admin_settings, get_monthly_usage

    ensure_llm_admin_defaults()
    from config.llm_config import OPENAI_MONTHLY_BUDGET_JPY, OPENAI_SESSION_COST_ALERT_JPY

    return {
        "settings": get_admin_settings(),
        "monthly_usage": get_monthly_usage(),
        "budget_jpy": OPENAI_MONTHLY_BUDGET_JPY,
        "session_alert_jpy": OPENAI_SESSION_COST_ALERT_JPY,
    }


@app.post("/admin/llm_settings")
async def admin_llm_settings_post(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    if not _require_admin(request, creds):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data, err = await _read_json_dict(request)
    if err:
        return err
    from src.services.budget_guard import (
        set_admin_settings,
        set_admin_message,
        set_alert_email,
        get_admin_settings,
    )

    if "alert_email" in data:
        set_alert_email(data.get("alert_email") or "")
    messages = data.get("messages")
    if isinstance(messages, dict):
        settings = get_admin_settings()
        merged = dict(settings.get("messages") or {})
        merged.update(messages)
        for key, text in merged.items():
            set_admin_message(key, text or "")
    if data.get("replace_settings"):
        set_admin_settings(data["replace_settings"])
    return {"status": "ok", "settings": get_admin_settings()}


@app.get("/admin/golden_cases")
def admin_golden_cases_list(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    if not _require_admin(request, creds):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from src.services.admin_settings_service import list_golden_cases

    return {"cases": list_golden_cases()}


@app.get("/admin/golden_cases/export")
def admin_golden_cases_export(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    if not _require_admin(request, creds):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    from src.services.admin_settings_service import export_golden_jsonl

    body = export_golden_jsonl()
    return Response(
        content=body,
        media_type="application/x-ndjson",
        headers={"Content-Disposition": 'attachment; filename="golden_cases.jsonl"'},
    )


@app.post("/admin/golden_cases")
async def admin_golden_cases_create(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    if not _require_admin(request, creds):
        return JSONResponse({"error": "Unauthorized"}, status_code=401)
    data, err = await _read_json_dict(request)
    if err:
        return err
    if not data.get("input_text") or not data.get("expected_category"):
        return JSONResponse(
            {"status": "error", "message": "input_text and expected_category are required"},
            status_code=400,
        )
    from src.services.admin_settings_service import insert_golden_case

    new_id = insert_golden_case(data)
    if new_id is None:
        return JSONResponse({"status": "error", "message": "DB unavailable"}, status_code=503)
    return {"status": "ok", "id": new_id}


@app.post("/admin/ai_control")
async def admin_ai_control_route(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    mode = data.get("mode")
    if mode == "on":
        set_ai_auto_reply(True)
        message = "AI自動応答をONにしました"
    elif mode == "off":
        set_ai_auto_reply(False)
        message = "AI自動応答をOFFにしました"
    else:
        return JSONResponse({"status": "error", "message": "無効なモード"}, status_code=400)
    logger.info("🤖 AI自動応答: %s (グローバル設定)", str(mode).upper())
    return {"status": "ok", "message": message, "ai_auto_reply": get_ai_auto_reply()}


@app.post("/admin/medicine_chat")
async def admin_medicine_chat_route(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    user_message = (data.get("message") or "").strip()
    if not user_message:
        return JSONResponse({"status": "error", "message": "メッセージが空です"}, status_code=400)
    start_time = time.time()
    from src.core.medicine_logic import (
        analyze_symptoms_and_medicine_type,
        comprehensive_medicine_recommendation,
        rule_based_medicine_recommendation,
        select_symptoms_via_gpt,
    )

    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            logger.error("❌ OPENAI_API_KEY が環境変数に設定されていません")
            add_network_log(
                "POST",
                "管理画面 - 医薬品相談テスト",
                {"message": user_message},
                None,
                time.time() - start_time,
                "failed",
                "OpenAI APIキーが設定されていません",
            )
            return JSONResponse(
                {
                    "status": "error",
                    "message": "OpenAI APIキーが設定されていません",
                    "error": "環境変数 OPENAI_API_KEY を設定してください",
                },
                status_code=500,
            )
        from openai import OpenAI

        test_client = OpenAI(api_key=api_key)
        symptoms_result = select_symptoms_via_gpt(user_message, None, test_client)
        if symptoms_result and symptoms_result.get("status") == "success":
            symptoms = symptoms_result.get("symptoms", [])
            medicine_type_result = analyze_symptoms_and_medicine_type(user_message, test_client)
            if medicine_type_result and medicine_type_result.get("medicine_type"):
                recommendation = rule_based_medicine_recommendation(
                    user_text=user_message, user_info={}, client=test_client
                )
                clean_recommendation = _clean_nan(recommendation)
                rule_names = [
                    (m.get("product_name") or m.get("name") or "")
                    for m in (recommendation.get("recommended_medicines") or [])[:3]
                ]
                gpt_names: list = []
                try:
                    from src.core.medicine.medicine_recommendation_gpt import recommend_medicines_with_retry

                    gpt_rec = recommend_medicines_with_retry(
                        user_message,
                        symptoms,
                        [],
                        user_info={},
                        client=test_client,
                    )
                    gpt_names = [
                        (m.get("product_name") or m.get("name") or "")
                        for m in (gpt_rec.get("recommended_medicines") or [])[:3]
                    ]
                except Exception as cmp_err:
                    logger.debug("GPT compare skipped: %s", cmp_err)
                try:
                    from src.services.admin_settings_service import log_medicine_compare

                    log_medicine_compare(
                        session_id=f"admin-{int(time.time())}",
                        rule_meds=rule_names,
                        gpt_meds=gpt_names,
                    )
                except Exception as log_err:
                    logger.debug("compare log skipped: %s", log_err)
                response_time = time.time() - start_time
                add_network_log(
                    "POST",
                    "管理画面 - 医薬品相談テスト",
                    {"message": user_message, "type": "rule_based"},
                    clean_recommendation,
                    response_time,
                    "success",
                    None,
                )
                logger.info("✅ 医薬品相談テスト成功（ルールベース）: %.2f秒", response_time)
                return {
                    "status": "ok",
                    "message": "医薬品推奨を実行しました",
                    "symptoms": symptoms,
                    "medicine_type": medicine_type_result["medicine_type"],
                    "recommendation": clean_recommendation,
                    "compare": {"rule": rule_names, "gpt": gpt_names},
                }
            recommendation = comprehensive_medicine_recommendation(user_text=user_message, client=test_client)
            clean_recommendation = _clean_nan(recommendation)
            response_time = time.time() - start_time
            add_network_log(
                "POST",
                "管理画面 - 医薬品相談テスト",
                {"message": user_message, "type": "ai_based"},
                clean_recommendation,
                response_time,
                "success",
                None,
            )
            logger.info("✅ 医薬品相談テスト成功（AI）: %.2f秒", response_time)
            return {
                "status": "ok",
                "message": "医薬品推奨を実行しました（AI）",
                "symptoms": symptoms,
                "recommendation": clean_recommendation,
            }
        return JSONResponse(
            {"status": "error", "message": "症状抽出に失敗しました", "details": symptoms_result},
            status_code=500,
        )
    except Exception as e:
        logger.error("❌ 医薬品相談テストエラー: %s", str(e))
        logger.error(traceback.format_exc())
        response_time = time.time() - start_time
        add_network_log(
            "POST",
            "管理画面 - 医薬品相談テスト",
            {"message": user_message},
            None,
            response_time,
            "failed",
            str(e),
        )
        return JSONResponse(
            {"status": "error", "message": "エラーが発生しました", "error": str(e)},
            status_code=500,
        )


@app.post("/clear_logs")
def clear_logs():
    network_logs.clear()
    db = get_database()
    if db and (db.connection or db.connection_pool):
        all_sessions = get_all_sessions_from_db()
        for sess_id in list(all_sessions.keys()):
            try:
                db.delete_session(sess_id)
            except Exception:
                pass
        logger.info("🗑️ All sessions cleared from database")
    else:
        clear_sessions_fallback()
        logger.warning("⚠️ DB unavailable, cleared memory sessions only")
    set_manual_reply_queue([])
    log_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "log", "recommendation_log.jsonl")
    if os.path.exists(log_file):
        try:
            with open(log_file, "w", encoding="utf-8"):
                pass
            logger.info("📝 ログファイルをクリアしました")
        except Exception as e:
            logger.error("❌ ログファイルのクリアに失敗: %s", e)
    logger.info("🗑️ ログ、セッション履歴、手動返信待ちキューをすべてクリアしました")
    return {"status": "ok", "message": "ログ、セッション履歴、手動返信待ちキューをクリアしました"}


@app.get("/api/admin/sessions")
def api_admin_sessions(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    cleanup_old_sessions(
        force=True,
        exclude_current_session=False,
        current_sid=None,
        skip_empty_sessions=True,
    )
    sessions_data = []
    all_sessions = get_all_sessions_from_db()
    for sess_id, info in all_sessions.items():
        if not isinstance(info, dict):
            continue
        sessions_data.append(
            {
                "session_id": str(sess_id),
                "username": str(info.get("username", "Unknown")),
                "messages": list(info.get("messages", []) or []),
                "last_activity": info.get("last_activity", 0),
                "session_active": bool(info.get("session_active", True)),
                "client_ip": str(info.get("client_ip", "")),
                "user_agent": str(info.get("user_agent", "")),
                "user_attributes": dict(info.get("user_attributes", {}) or {}),
                "detailed_diagnosis": info.get("detailed_diagnosis"),
                "message_count": len(info.get("messages", []) or []),
            }
        )
    return {"sessions": sessions_data, "admin_mode": bool(get_admin_mode()), "ai_auto_reply": bool(get_ai_auto_reply())}


@app.post("/api/admin/sessions/purge_empty")
def api_admin_purge_empty_sessions(
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    db = get_database()
    if not db or not (db.connection or db.connection_pool):
        return JSONResponse({"status": "error", "message": "データベース接続エラー"}, status_code=500)
    exclude = get_cleanup_exclude_session_ids()
    deleted = db.purge_all_empty_sessions(exclude_session_ids=exclude)
    return {"status": "success", "deleted_count": deleted, "message": f"{deleted}件の空セッションを削除しました"}


@app.delete("/api/admin/sessions/{session_id}")
def api_admin_delete_session(
    session_id: str,
    request: Request,
    creds: HTTPBasicCredentials | None = Depends(security_basic),
):
    auth_err = _admin_json_guard(request, creds)
    if auth_err:
        return auth_err
    if delete_session_by_id(session_id):
        return {"status": "success", "message": "セッションを削除しました"}
    return JSONResponse({"status": "error", "message": "セッションが見つかりませんでした"}, status_code=404)


@app.delete("/api/admin/sessions/delete_all")
def api_admin_delete_all_sessions():
    db = get_database()
    if db and (db.connection or db.connection_pool):
        deleted_count = db.delete_all_sessions()
        return {"status": "success", "message": f"{deleted_count}件のセッションを削除しました", "deleted_count": deleted_count}
    return JSONResponse({"status": "error", "message": "データベース接続エラー"}, status_code=500)


@app.put("/api/admin/sessions/{session_id}")
async def api_admin_update_session(session_id: str, request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    session_data = get_session_from_db(session_id)
    if not session_data:
        return JSONResponse({"status": "error", "message": "セッションが見つかりませんでした"}, status_code=404)
    if "username" in data:
        session_data["username"] = data["username"]
    if "session_active" in data:
        session_data["session_active"] = data["session_active"]
    if "user_attributes" in data:
        session_data["user_attributes"] = data["user_attributes"]
    session_data["last_activity"] = datetime.now()
    save_session_to_db(session_id, session_data)
    return {"status": "success", "message": "セッション情報を更新しました"}


@app.post("/api/admin/send_message")
async def api_admin_send_message(request: Request):
    data, err = await _read_json_dict(request)
    if err:
        return err
    session_id = data.get("session_id")
    message = data.get("message")
    if not session_id or not message:
        return JSONResponse({"status": "error", "message": "session_idとmessageが必要です"}, status_code=400)
    session_data = get_session_from_db(session_id)
    if not session_data:
        return JSONResponse({"status": "error", "message": "セッションが見つかりません"}, status_code=404)
    ai_response = {"role": "ai", "content": message, "timestamp": datetime.now().isoformat(), "from_admin": True}
    session_data.setdefault("messages", [])
    session_data["messages"].append(ai_response)
    session_data["last_activity"] = datetime.now()
    save_session_to_db(session_id, session_data)
    return {"status": "success", "message": "メッセージを送信しました"}


@app.post("/api/request_admin")
def api_request_admin(request: Request, response: Response, sid: str = Depends(get_sid)):
    if not sid:
        return JSONResponse({"status": "error", "message": "No session"}, status_code=400)

    session_data = get_session_from_db(sid) or {
        "session_id": sid,
        "username": f"ユーザー{get_next_user_number()}",
        "messages": [],
        "last_activity": datetime.now(),
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("User-Agent", ""),
        "user_attributes": {},
        "session_active": True,
    }

    username = session_data.get("username", "unknown")
    session_data["admin_request"] = True
    session_data["ai_auto_reply"] = False
    system_message = {
        "type": "bot",
        "content": "薬剤師対応を要請しました。しばらくお待ちください。",
        "admin_request": True,
        "style_class": "admin-request",
    }
    session_data.setdefault("messages", [])
    session_data["messages"].append(system_message)
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)

    queue = get_manual_reply_queue()
    already_exists = any(item.get("session_id") == sid and item.get("admin_request") for item in queue)
    if not already_exists:
        queue.append(
            {
                "session_id": sid,
                "username": username,
                "user_message": "【薬剤師要請】" + username,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "status": "admin_requested",
                "admin_request": True,
            }
        )
        set_manual_reply_queue(queue)

    return {"status": "ok", "message": "薬剤師対応を要請しました"}


