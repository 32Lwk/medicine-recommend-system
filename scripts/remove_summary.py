path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# Remove lines 682-791 (1-based) = index 681-790
new_lines = lines[:681] + lines[791:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed generate_counseling_summary from counseling_response.py")
