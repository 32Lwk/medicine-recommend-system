# Extract process_counseling_answer (lines 124-682) to counseling_processor.py
path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# 1-based 124-682 -> index 123-681
block = lines[123:682]
content = "".join(block)
header = '''"""
カウンセリング回答の統合処理（process_counseling_answer）
"""
import json
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_format import format_conversation_history
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_summary import generate_counseling_summary
from src.services.counseling.counseling_questions import (
    should_generate_question_non_medical,
    generate_supportive_question,
)
from src.services.counseling.counseling_satisfaction import analyze_user_satisfaction

logger = logging.getLogger(__name__)

'''
with open("src/services/counseling/counseling_processor.py", "w", encoding="utf-8") as g:
    g.write(header + content)
print("Written counseling_processor.py", len(header) + len(content), "chars")
