import json

input_jsonl = "pr_2496.jsonl"
output_json = "predictions.json"
instance_id = "pylint-dev__astroid.b114f6b5.2496"

with open(input_jsonl, 'r') as f:
    for line in f:
        item = json.loads(line)
        if item["pull_number"] == 2496:
            # This patch is the FIX
            patch = item["patch"]
            break

entry = {
    "instance_id": instance_id,
    "model_patch": patch,
    "model_name_or_path": "gold"
}

# eval.py expects a dict {instance_id: entry} for .json files
output_data = {
    instance_id: entry
}

with open(output_json, 'w') as f:
    json.dump(output_data, f, indent=4)

print(f"Created {output_json}")
