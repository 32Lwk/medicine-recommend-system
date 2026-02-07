#!/usr/bin/env python3
"""Extract POST block to _handle_chat_post_impl in app.py and replace with handler call."""
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
APP_PATH = os.path.join(BASE, 'app.py')

with open(APP_PATH, 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.splitlines(keepends=True)

# Extract block 768-7491 (0-indexed: 767-7490) - POST block in index
block = lines[767:7491]
new_lines = []
for line in block:
    if line.strip() == '':
        new_lines.append(line)
    else:
        # Add 4 spaces to preserve relative indentation as function body
        new_lines.append('    ' + line)

impl_body = ''.join(new_lines)

# Remove the redundant "if request.method == 'POST':" - we are only called for POST
# After adding 4 spaces: if-line has 8 spaces, body has 12+. Drop if, subtract 4 from each line.
impl_lines = impl_body.splitlines(keepends=True)
if impl_lines and 'if request.method ==' in impl_lines[0]:
    impl_lines = impl_lines[1:]
    result = []
    for line in impl_lines:
        if line.strip() == '':
            result.append(line)
        elif len(line) >= 4 and line[:4] == '    ':
            result.append(line[4:])  # subtract 4
        else:
            result.append(line)
    impl_body = ''.join(result)

# Replace the POST block in index with the handler call
old_block = ''.join(lines[767:7491])
replacement = '''    if request.method == 'POST':
        from src.handlers.chat_handler import handle_chat_post
        return handle_chat_post(session, request, sid, monitor, client_ip, user_agent)
'''

# Find where to insert _handle_chat_post_impl (before @app.route('/', ...))
insert_marker = "@app.route('/', methods=['GET', 'POST'])"
idx = content.find(insert_marker)
if idx == -1:
    print("Could not find insert marker")
    exit(1)

# Insert the function before the route
func_def = '''
def _handle_chat_post_impl(session, request, sid, monitor, client_ip, user_agent):
    """Chat POST logic - extracted from index for SRP (Phase 2.4)."""
''' + impl_body + '\n\n'

# Build new content: replace the POST block in index with the call, and add the function
new_content = content[:idx] + func_def + content[idx:]

# Replace the POST block
new_content = new_content.replace(old_block, replacement, 1)

with open(APP_PATH, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Done. Replaced POST block with handler call, added _handle_chat_post_impl")
