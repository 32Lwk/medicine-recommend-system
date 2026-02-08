# Extract generate_counseling_response and personalize_response to counseling_generator.py
with open("src/services/counseling_response.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
# lines 68-716 (1-based) = index 67 to 715
block = lines[67:716]
content = "".join(block)
header = '''"""
カウンセリング返信の生成
"""
import logging
from typing import Dict, List
from openai import OpenAI

from src.services.counseling.counseling_templates import generate_illegal_drug_rejection_message
from src.services.counseling.counseling_logger import log_counseling_response
from src.services.counseling.counseling_prompts import get_counseling_prompt_template
from src.services.counseling.counseling_format import format_conversation_history

logger = logging.getLogger(__name__)

'''
with open("src/services/counseling/counseling_generator.py", "w", encoding="utf-8") as g:
    g.write(header + content)
print("Written counseling_generator.py", len(header) + len(content), "chars")
