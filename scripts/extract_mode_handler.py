# Extract start_counseling_mode (79-101) and handle_user_input_in_counseling_mode (125-416)
path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# 1-based: start 79-101 -> index 78-100; handle 125-416 -> index 124-415
start_block = "".join(lines[78:101])
handle_block = "".join(lines[124:416])
header = '''"""
カウンセリングモードの制御（start_counseling_mode, handle_user_input_in_counseling_mode）
format_conversation_history は counseling_format から re-export
"""
import logging
import re
from datetime import datetime
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_topic_shift import detect_topic_shift
from src.services.counseling.counseling_processor import process_counseling_answer

logger = logging.getLogger(__name__)

'''
content = header + start_block + "\n\n" + handle_block
with open("src/services/counseling/counseling_mode_handler.py", "w", encoding="utf-8") as g:
    g.write(content)
print("Written counseling_mode_handler.py", len(content), "chars")
