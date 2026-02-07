#!/usr/bin/env python3
"""Extract POST block from app.py to chat_post_processor.py"""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(BASE, 'app.py')
OUT_PATH = os.path.join(BASE, 'src', 'handlers', 'chat_post_processor.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    lines = f.readlines()

block = lines[443:6760]
new_lines = []
for line in block:
    if len(line) >= 8 and line[:8] == '        ':
        new_lines.append(line[4:])
    elif line.strip() == '':
        new_lines.append(line)
    else:
        new_lines.append(line)

header = '''"""
Chat POST processor - extracted from app.index()
"""

from flask import jsonify, render_template, request
from datetime import datetime
import time
import random
import re
import os
import logging

logger = logging.getLogger(__name__)

def process_chat_post(session, request, sid, monitor, client_ip, user_agent):
    """Process chat POST request."""
'''

with open(OUT_PATH, 'w', encoding='utf-8') as f:
    f.write(header)
    f.write(''.join(new_lines))

print('Created', OUT_PATH, len(header) + sum(len(l) for l in new_lines), 'chars')
