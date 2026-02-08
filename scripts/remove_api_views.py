# Remove api views from app.py: lines 102-823 (api_status through line before submit_feedback)
# and lines 958-1022 (translate_text, set_language). Keep 1-101, 824-957 (feedback), 1023-end.
path = "app.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# 0-based: keep 0-101, 823-957, 1022-end
new_lines = lines[:101] + lines[823:957] + lines[1022:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed api views (102-823 and 958-1022) from app.py")
