path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# process_counseling_answer: lines 124-682 (1-based) = index 123-681
new_lines = lines[:123] + lines[682:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed process_counseling_answer from counseling_response.py")
