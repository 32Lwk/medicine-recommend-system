"""
OpenAI クライアントの初期化のみ（責務: API キー取得と OpenAI() 呼び出し）

.env の読み込みと client 生成を集約。medicine_logic 等から import して利用する。
"""
import os
import logging

logger = logging.getLogger(__name__)

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
    if os.getenv("DEBUG_MODE", "false").lower() == "true":
        logger.debug("[DEBUG] load_dotenv() 実行済み")
except ImportError:
    pass

try:
    from config.llm_config import get_openai_api_key
    api_key = get_openai_api_key()
except ImportError:
    api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    logger.warning("WARNING: OpenAI API keyが環境変数に設定されていません。")

from openai import OpenAI

client = None
if api_key:
    try:
        client = OpenAI(api_key=api_key)
        if os.getenv("DEBUG_MODE", "false").lower() == "true":
            logger.debug("OpenAI client initialized successfully.")
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {e}")
else:
    logger.error("OpenAI API key not found. Set OPENAI_API_KEY in environment or .env.")
