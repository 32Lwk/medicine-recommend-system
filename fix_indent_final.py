#!/usr/bin/env python3
"""
if is_question:ブロックのインデント修正
267行目から1159行目までのインデントを4スペース減らす
"""

# ファイルを読み込む
with open('app.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# 663行目から1159行目までのインデントを4スペース減らす
for i in range(662, 1159):  # 0-based index
    if i >= len(lines):
        break
    
    line = lines[i]
    
    # 空行はスキップ
    if not line.strip():
        continue
    
    # 現在のインデントを測定
    stripped = line.lstrip(' ')
    current_indent = len(line) - len(stripped)
    
    # 20スペース以上のインデントがある行は4スペース減らす
    if current_indent >= 20:
        new_indent = current_indent - 4
        lines[i] = ' ' * new_indent + stripped

# ファイルに書き戻す
with open('app.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Final indent fix completed")

