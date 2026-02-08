path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# detect_topic_shift: lines 683-777 (1-based) = index 682-776
new_lines = lines[:682] + lines[777:]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed detect_topic_shift from counseling_response.py")
