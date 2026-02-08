# Remove the placeholder and old function body (lines 71-721) from counseling_response.py
path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# Keep lines 1-70 (index 0-69), then lines from 722 (index 721) to end
new_lines = lines[:70] + lines[721:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed lines 71-721 from counseling_response.py")
