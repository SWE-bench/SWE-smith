import json
from pathlib import Path

import modal

app = modal.App("swesmith-upload-hf")
vol = modal.Volume.from_name("swesmith-bug-gen")
image = modal.Image.debian_slim().pip_install("datasets", "huggingface_hub")

REQUIRED_KEYS = [
    "instance_id",
    "patch",
    "FAIL_TO_PASS",
    "PASS_TO_PASS",
    "image_name",
    "repo",
]
ISSUE_MODEL_KEY = "portkey/gpt-5-mini"


def _attach_issue_statement(task: dict, issue_gen_dir: Path, repo_id: str) -> dict:
    """Attach issue text and normalize fields for a task instance."""
    instance_id = task.get("instance_id")
    if not instance_id:
        return task

    if "image_name" in task and ".architecture." in task["image_name"]:
        task["image_name"] = task["image_name"].replace(".architecture", "")

    task["problem_statement"] = ""
    issue_file = issue_gen_dir / repo_id / f"{instance_id}.json"
    if not issue_file.exists():
        return task

    try:
        issue_data = json.loads(issue_file.read_text())
    except Exception:
        return task

    responses = issue_data.get("responses", {})
    content = responses.get(ISSUE_MODEL_KEY)
    if isinstance(content, list) and content:
        task["problem_statement"] = content[0]

    return task


@app.function(
    image=image,
    volumes={"/data": vol},
    secrets=[modal.Secret.from_name("john-hf-secret")],
    timeout=10800,
)
def upload_from_volume_remote(
    target_dataset: str, language: str = "javascript"
) -> dict:
    """Robust end-to-end upload: volume -> issue merge -> validate -> HF push."""
    import os
    from datasets import Dataset
    from huggingface_hub import create_repo

    token = os.environ.get("HF_TOKEN")
    if not token:
        return {"success": False, "error": "HF_TOKEN not found in environment"}

    task_insts_dir = Path(f"/data/{language}/task_insts")
    issue_gen_dir = Path(f"/data/{language}/issue_gen")
    if not task_insts_dir.exists():
        return {"success": False, "error": f"Missing task_insts dir: {task_insts_dir}"}

    task_files = sorted(task_insts_dir.glob("*.json"))
    if not task_files:
        return {"success": False, "error": f"No task files in {task_insts_dir}"}

    print(f"Found {len(task_files)} task files in volume.")

    cleaned_tasks = []
    skipped_missing_keys = 0
    repos_processed = 0
    repos_failed = 0

    for task_file in task_files:
        repo_id = task_file.stem
        try:
            tasks = json.loads(task_file.read_text())
        except Exception as e:
            repos_failed += 1
            print(f"[{repo_id}] Failed to read tasks: {e}")
            continue

        repos_processed += 1
        print(f"[{repo_id}] Processing {len(tasks)} tasks...")

        for task in tasks:
            task = _attach_issue_statement(task, issue_gen_dir, repo_id)
            if all(k in task for k in REQUIRED_KEYS):
                if "problem_statement" not in task:
                    task["problem_statement"] = ""
                cleaned_tasks.append(task)
            else:
                skipped_missing_keys += 1

        print(f"[{repo_id}] Done")

    if not cleaned_tasks:
        return {
            "success": False,
            "error": "No valid tasks to upload",
            "repos_processed": repos_processed,
            "repos_failed": repos_failed,
            "skipped_missing_keys": skipped_missing_keys,
        }

    print(f"Valid tasks: {len(cleaned_tasks)}")
    dataset = Dataset.from_list(cleaned_tasks)

    print(f"Ensuring dataset repo exists: {target_dataset}")
    create_repo(target_dataset, repo_type="dataset", token=token, exist_ok=True)

    print(f"Pushing {len(dataset)} instances to {target_dataset}...")
    dataset.push_to_hub(target_dataset, token=token)
    print("Remote push finished successfully.")

    return {
        "success": True,
        "target_dataset": target_dataset,
        "repos_processed": repos_processed,
        "repos_failed": repos_failed,
        "instances_uploaded": len(cleaned_tasks),
        "skipped_missing_keys": skipped_missing_keys,
    }


@app.local_entrypoint()
def main(
    target_dataset: str = "SWE-bench/SWE-smith-js",
    language: str = "javascript",
    push: bool = False,
):
    if not push:
        confirm = input(
            f"Run remote upload to '{target_dataset}' for language '{language}'? (y/n) "
        ).lower()
        if confirm != "y":
            print("Aborting.")
            return

    print("Starting robust remote upload...")
    result = upload_from_volume_remote.remote(target_dataset, language)
    print(json.dumps(result, indent=2))

    if not result.get("success"):
        raise RuntimeError(result.get("error", "Upload failed"))
