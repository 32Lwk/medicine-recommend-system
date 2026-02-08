# Remove admin view functions from app.py (lines 578-1061, 1-based)
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# Keep 1-577, then 1062-end
new_lines = lines[:577] + lines[1061:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed admin views from app.py (lines 578-1061)")
