import json
import os

# Config
bug_diff_path = "logs/bug_gen/pylint-dev__astroid.b114f6b5/pr_mirror/pylint-dev__astroid.b114f6b5.2496/bug__pr_2496.diff"
repo = "pylint-dev__astroid.b114f6b5"
instance_id = "pylint-dev__astroid.b114f6b5.2496"
input_jsonl = "pr_2496.jsonl"
output_json = "validation_input.json"

# Read test_patch from original input
test_patch = ""
with open(input_jsonl, 'r') as f:
    for line in f:
        item = json.loads(line)
        if item["pull_number"] == 2496:
            test_patch = item["test_patch"]
            break

with open(bug_diff_path, 'r') as f:
    patch_content = f.read()

data = [{
    "instance_id": instance_id,
    "patch": patch_content,
    "repo": repo,
    "instance_ref": {
        "test_patch": test_patch
    }
}]

with open(output_json, 'w') as f:
    json.dump(data, f, indent=4)

print(f"Created {output_json}")
