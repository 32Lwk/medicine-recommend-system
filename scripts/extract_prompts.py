"""Extract get_counseling_prompt_template to counseling_prompts.py"""
with open("src/services/counseling_response.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
block = lines[65:529]
content = "".join(block)
header = '''"""
プロンプトテンプレート取得（症状タイプ別）
"""
from typing import Dict, Any

'''
with open("src/services/counseling/counseling_prompts.py", "w", encoding="utf-8") as g:
    g.write(header + content)
print("Written", len(header) + len(content), "chars")
