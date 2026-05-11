import json
import logging
import math
import os
import re
from pathlib import Path
import random
import time
import traceback
from datetime import datetime
from urllib.parse import unquote
from xml.sax.saxutils import escape

import pytz
from fastapi import Depends, FastAPI, Form, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.responses import FileResponse, Response as StarletteResponse

from config.app_config import configure_logging, get_cors_config, get_session_config, load_env
from src.core.season_manager import get_current_season, get_season_images
from src.handlers.chat_handler import handle_chat_post
from src.utils.chat_http_context import ChatClientInfo
from src.services.database import init_database
from src.services.database import get_database
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
    save_session_to_db,
    set_admin_mode,
    set_ai_auto_reply,
    set_manual_reply_message,
    set_manual_reply_queue,
)
from src.utils.performance_monitor import get_global_monitor
from src.utils.request_safe_session import RequestSafeSession
from src.utils.debug_logger import performance_stats, network_logs, add_network_log

configure_logging()
load_env()
logger = logging.getLogger(__name__)


def _compute_cookie_settings() -> dict:
    cfg = get_session_config()
    # Flask config keys -> Starlette cookie options
    return {
        "secure": bool(cfg.get("SESSION_COOKIE_SECURE", False)),
        "samesite": cfg.get("SESSION_COOKIE_SAMESITE", "lax"),
        "httponly": bool(cfg.get("SESSION_COOKIE_HTTPONLY", False)),
        # domain/path/max_age are left as defaults (domain None, path '/')
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


def get_sid(request: Request, response: Response) -> str:
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


app = FastAPI(redirect_slashes=False)
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
    # templates/*.html は Flask の url_for('static', filename=...) を使用している。
    if endpoint == "static":
        filename = values.get("filename") or values.get("path") or ""
        if filename.startswith("/"):
            filename = filename[1:]
        return f"/static/{filename}"
    raise KeyError(f"Unsupported url_for endpoint: {endpoint}")


templates.env.globals["url_for"] = _compat_url_for


@app.exception_handler(StarletteHTTPException)
async def _http_exception_handler(request: Request, exc: StarletteHTTPException):
    """404 は Flask 同様 index.html を返す。それ以外は JSON。"""
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
                "error_type": error_type if os.getenv("FLASK_ENV") != "production" else None,
            },
            status_code=500,
        )
    return HTMLResponse(f"<h1>エラー</h1><p>{error_msg}</p>", status_code=500)


@app.on_event("startup")
def _startup():
    try:
        init_database()
    except Exception as e:
        logger.warning(f"⚠️ Database startup unexpected error: {e}. Feedback features will be disabled.")


def _render_index(request: Request, sid: str, app_base_path: str, status_code: int = 200) -> HTMLResponse:
    # 互換: Flask 版は VERSION を app.config に置くが、ここでは毎プロセスで固定。
    nv = _normalized_app_version_env()
    version = nv if nv is not None else str(int(time.time()))
    session_like = {"_id": sid} if sid else {}
    decoration_images, image_version = _get_decoration_images(session_like, version)

    return templates.TemplateResponse(
        request,
        "index.html",
        {
            "messages": [],
            "version": version,
            "username": "Unknown",
            "decoration_images": decoration_images,
            "image_version": image_version,
            "app_base_path": app_base_path,
        },
        status_code=status_code,
    )


@app.get("/", response_class=HTMLResponse)
def get_root(request: Request, response: Response, sid: str = Depends(get_sid)):
    return _render_index(request, sid, app_base_path="")


@app.get("/test/", response_class=HTMLResponse)
def get_test_root(request: Request, response: Response, sid: str = Depends(get_sid)):
    return _render_index(request, sid, app_base_path="/test")


@app.get("/favicon.ico")
def favicon():
    if not _FAVICON_PATH.is_file():
        return StarletteResponse(status_code=204)
    return FileResponse(_FAVICON_PATH, media_type="image/png")


@app.get("/sitemap.xml")
def sitemap():
    base = (os.getenv("PUBLIC_SITE_URL") or "https://medicine.yutok.dev").rstrip("/")
    loc = escape(f"{base}/", {'"': "&quot;", "'": "&apos;"})
    body = (
        "<?xml version=\"1.0\" encoding=\"UTF-8\"?>"
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f"<url><loc>{loc}</loc><changefreq>weekly</changefreq><priority>1.0</priority></url>"
        "</urlset>"
    )
    return StarletteResponse(content=body, media_type="application/xml; charset=utf-8")


def _prime_safe_session_for_chat(safe_session: RequestSafeSession, sid: str, request: Request):
    """
    Flask 実装（main_routes.index）に近い初期化を FastAPI 側で再現し、
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
    client_info = ChatClientInfo.from_starlette_request(request)
    monitor = get_global_monitor()
    monitor.start_monitoring()
    monitor.increment_request()

    safe_session = RequestSafeSession()
    _prime_safe_session_for_chat(safe_session, sid, request)

    body, status_code = handle_chat_post(safe_session, client_info, message, sid, monitor)
    if not isinstance(body, dict) or not isinstance(status_code, int):
        body = {"error": True, "response": "サーバーから予期しない形式のレスポンスが返されました"}
        status_code = 500
    return JSONResponse(content=body, status_code=status_code)


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


@app.post("/clear")
def clear_chat(request: Request, response: Response, sid: str = Depends(get_sid)):
    if sid:
        session_data = get_session_from_db(sid)
        if session_data:
            session_data["messages"] = []
            save_session_to_db(sid, session_data)
    return Response(status_code=204)


@app.post("/test/clear")
def clear_chat_test(request: Request, response: Response, sid: str = Depends(get_sid)):
    return clear_chat(request, response, sid)


@app.post("/new_session")
def new_session(request: Request, response: Response):
    # 新規SIDを発行してcookieを書き換える
    sid = str(int(time.time() * 1000)) + str(random.randint(100000, 999999))
    response.set_cookie(COOKIE_NAME_SID, sid, **COOKIE_SETTINGS)
    username = f"ユーザー{get_next_user_number()}"

    session_data = {
        "session_id": sid,
        "username": username,
        "messages": [],
        "last_activity": datetime.now(),
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("User-Agent", ""),
        "user_attributes": {},
        "session_active": True,
    }
    save_session_to_db(sid, session_data)

    return {"message": "新しいセッションを開始しました", "username": username}


@app.post("/test/new_session")
def new_session_test(request: Request, response: Response):
    return new_session(request, response)


@app.get("/api/sessions")
def api_sessions_get(
    request: Request,
    response: Response,
    sid: str = Depends(get_sid),
):
    # Flask実装の互換: DBが無ければフォールバックもあるが、ここでは session_manager に委譲。
    # まずDBから取得、無ければ最小レコードを作成
    session_data = get_session_from_db(sid)
    if not session_data:
        session_data = {
            "session_id": sid,
            "username": f"ユーザー{get_next_user_number()}",
            "messages": [],
            "session_active": True,
            "last_activity": datetime.now(),
            "client_ip": request.client.host if request.client else "",
            "user_agent": request.headers.get("User-Agent", ""),
            "user_attributes": {},
        }
        save_session_to_db(sid, session_data)
    else:
        session_data["last_activity"] = datetime.now()
        save_session_to_db(sid, session_data)

    messages = session_data.get("messages", []) or []
    user_attributes = session_data.get("user_attributes", {}) or {}

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
    session_data = get_session_from_db(sid) or {
        "session_id": sid,
        "username": f"ユーザー{get_next_user_number()}",
        "messages": [],
        "session_active": True,
        "last_activity": datetime.now(),
        "client_ip": request.client.host if request.client else "",
        "user_agent": request.headers.get("User-Agent", ""),
        "user_attributes": {},
    }
    session_data["user_attributes"] = user_attributes
    session_data["last_activity"] = datetime.now()
    save_session_to_db(sid, session_data)
    return {"status": "ok", "message": "ユーザー情報を保存しました"}

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

    db = get_database()
    if not (db and (db.connection or db.connection_pool)):
        return JSONResponse({"error": "Database not available"}, status_code=500)

    required_fields = ["report_type", "user_message", "ai_response"]
    for field in required_fields:
        if field not in data:
            return JSONResponse({"error": f"Missing required field: {field}"}, status_code=400)

    # レート制限（sid単位、60秒）
    if sid:
        session_data = get_session_from_db(sid) or {}
        current_time = time.time()
        last_feedback_time = session_data.get("last_feedback_time", 0) or 0
        if current_time - last_feedback_time < 60:
            return JSONResponse({"error": "Rate limit exceeded. Please wait 60 seconds."}, status_code=429)
        session_data["last_feedback_time"] = current_time
        save_session_to_db(sid, session_data)

    feedback_text = data.get("feedback_text", "") or ""
    if len(feedback_text) > 1000:
        return JSONResponse({"error": "Feedback text too long (max 1000 characters)"}, status_code=400)

    # DBへ保存
    session_data = get_session_from_db(sid) or {}
    username = session_data.get("username") or "Unknown"
    feedback_id = db.insert_feedback(
        report_type=data["report_type"],
        session_id=sid,
        username=username,
        user_message=data["user_message"],
        ai_response=data["ai_response"],
        security_score=data.get("security_score"),
        feedback_text=feedback_text,
        is_google_form=bool(data.get("is_google_form", False)),
    )
    if feedback_id:
        return {"status": "success", "feedback_id": feedback_id}
    return JSONResponse({"error": "Failed to save feedback"}, status_code=500)


@app.get("/api/get_feedback_reports")
def get_feedback_reports(limit: int = 100, unresolved_only: bool = False):
    db = get_database()
    if not (db and (db.connection or db.connection_pool)):
        return JSONResponse({"error": "Database not available"}, status_code=500)
    reports = db.get_feedback_reports(limit=limit, unresolved_only=unresolved_only)
    return {"reports": reports}


@app.post("/api/resolve_feedback/{feedback_id}")
def resolve_feedback(feedback_id: int):
    db = get_database()
    if not (db and (db.connection or db.connection_pool)):
        return JSONResponse({"error": "Database not available"}, status_code=500)
    if db.resolve_feedback(feedback_id):
        return {"status": "success"}
    return JSONResponse({"error": "Failed to resolve feedback"}, status_code=500)


@app.post("/api/delete_feedback/{feedback_id}")
def delete_feedback(feedback_id: int):
    db = get_database()
    if not (db and (db.connection or db.connection_pool)):
        return JSONResponse({"error": "Database not available"}, status_code=500)
    if db.delete_feedback(feedback_id):
        return {"status": "success"}
    return JSONResponse({"error": "Failed to delete feedback"}, status_code=500)


def _require_admin(credentials: HTTPBasicCredentials | None) -> bool:
    if not credentials:
        return False
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    return credentials.username == "admin" and credentials.password == admin_password


@app.get("/admin", response_class=HTMLResponse)
def admin_page(request: Request, creds: HTTPBasicCredentials | None = Depends(security_basic)):
    if not _require_admin(creds):
        headers = {"WWW-Authenticate": 'Basic realm="Admin Area"'}
        return Response(content="認証が必要です", status_code=401, headers=headers)
    return templates.TemplateResponse(request, "admin_chat.html", {})


@app.get("/api/main_sessions")
def api_main_sessions(sid: str = Depends(get_sid)):
    # Flask実装に寄せて force cleanup は省略（セッションDB正）
    all_sessions = get_all_sessions_from_db()
    sessions_list = []
    for sess_id, info in all_sessions.items():
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
        sessions_list.append(
            {
                "session_id": sess_id,
                "username": info.get("username", "Unknown"),
                "messages": info.get("messages", []),
                "last_activity": info.get("last_activity", 0),
                "message_count": len(info.get("messages", []) or []),
                "user_info": info.get("user_attributes", {}),
                "attributes": info.get("user_attributes", {}),
                "detailed_diagnosis": detailed_diag,
            }
        )
    return {"sessions": sessions_list}


@app.get("/api/main_manual_reply_queue")
def api_main_manual_reply_queue():
    return get_manual_reply_queue()


@app.post("/api/main_manual_reply_queue")
async def api_main_manual_reply_queue_post(request: Request):
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

    if action == "reply":
        message = data.get("reply_message") or data.get("message")
        if session_id and message:
            session_data = get_session_from_db(session_id)
            if session_data:
                manual_reply = {
                    "type": "bot",
                    "content": message,
                    "timestamp": datetime.now().isoformat(),
                    "manual_reply": True,
                }
                session_data.setdefault("messages", [])
                session_data["messages"].append(manual_reply)
                session_data["last_activity"] = datetime.now()
                save_session_to_db(session_id, session_data)
                queue = [q for q in queue if q.get("session_id") != session_id]
                set_manual_reply_queue(queue)
                return {"status": "success", "message": "メッセージを送信しました"}
        return JSONResponse({"status": "error", "message": "無効なアクションです"}, status_code=400)

    return JSONResponse({"status": "error", "message": "無効なアクションです"}, status_code=400)


@app.get("/api/main_ai_control")
def api_main_ai_control():
    return {
        "ai_auto_reply": get_ai_auto_reply(),
        "admin_mode": get_admin_mode(),
        "manual_reply_message": get_manual_reply_message(),
    }


@app.post("/api/main_ai_control")
async def api_main_ai_control_post(request: Request):
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
        resp = client.chat.completions.create(
            model="gpt-4o-mini",
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

    return {
        "status": "ok",
        "csv_load_status": csv_load_status,
        "total_sessions": len(all_sessions),
        "active_sessions": active_sessions,
        "manual_reply_queue": len(get_manual_reply_queue()),
        "ai_auto_reply": get_ai_auto_reply(),
        "admin_mode": get_admin_mode(),
        "performance_stats": performance_stats,
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
def api_admin_sessions(request: Request, sid: str = Depends(get_sid)):
    cleanup_old_sessions(force=True, exclude_current_session=True, current_sid=sid)
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
            }
        )
    return {"sessions": sessions_data, "admin_mode": bool(get_admin_mode()), "ai_auto_reply": bool(get_ai_auto_reply())}


@app.delete("/api/admin/sessions/{session_id}")
def api_admin_delete_session(session_id: str):
    db = get_database()
    if db and (db.connection or db.connection_pool):
        if db.delete_session(session_id):
            return {"status": "success", "message": "セッションを削除しました"}
        return JSONResponse({"status": "error", "message": "セッションが見つかりませんでした"}, status_code=404)
    return JSONResponse({"status": "error", "message": "データベース接続エラー"}, status_code=500)


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


