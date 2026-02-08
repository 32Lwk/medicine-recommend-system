"""Remove favicon, index, clear_chat, new_session from app.py (views moved to main_routes)."""
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()

# 1-based: favicon 102, clear_chat ends 252 -> remove 101-252 (index 100-251)
# Then new_session: originally 659-690 -> after removal 659-151=508, so index 507-539
new_lines = lines[:101] + lines[252:]
# Now new_session was at 659, now at 659-151=508. Remove 507-540 (0-based)
new_lines = new_lines[:507] + new_lines[540:]

with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed favicon, index, clear_chat, new_session from app.py")
