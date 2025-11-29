import json

task_file = "logs/task_insts/pylint-dev__astroid.b114f6b5.json"
issue_file = "temp_astroid_2496/issue_2492.txt"

with open(issue_file, "r") as f:
    problem_statement = f.read()

with open(task_file, "r") as f:
    data = json.load(f)

for item in data:
    item["problem_statement"] = problem_statement

with open(task_file, "w") as f:
    json.dump(data, f, indent=4)

print(f"Updated {len(data)} instances in {task_file}")

