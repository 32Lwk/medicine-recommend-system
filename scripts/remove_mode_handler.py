path = "src/services/counseling_response.py"
with open(path, "r", encoding="utf-8") as f:
    lines = f.readlines()
# Remove from "def _removed_start_counseling_mode" through end of handle_user_input (through "return process_counseling_answer...")
# Find the line index of "def _removed_start_counseling_mode" and the last line of the file
start_idx = None
for i, line in enumerate(lines):
    if "def _removed_start_counseling_mode(" in line:
        start_idx = i
        break
if start_idx is None:
    # try without placeholder - remove from "def start_counseling_mode"
    for i, line in enumerate(lines):
        if line.strip().startswith("def start_counseling_mode("):
            start_idx = i
            break
if start_idx is None:
    raise SystemExit("Could not find start of block")
# Remove from start_idx to end (inclusive)
new_lines = lines[:start_idx] + ["\n"]
with open(path, "w", encoding="utf-8") as f:
    f.writelines(new_lines)
print("Removed mode handler block from line", start_idx + 1)
