with open("src/services/counseling_response.py", "r", encoding="utf-8") as f:
    lines = f.readlines()
# Remove lines 67-518 (1-based), i.e. index 66 to 517
new_lines = lines[:66] + lines[518:]
with open("src/services/counseling_response.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed lines 67-518, kept", len(new_lines), "lines")
