import json
import os
from pathlib import Path

import modal

from scripts.bug_gen_modal import generator_image

VOLUME_NAME = "swesmith-bug-gen"
LOGS_MOUNT_PATH = "/logs"

app = modal.App("issue-gen-redo-existing")
logs_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True, version=2)


@app.function(
    image=generator_image,
    volumes={LOGS_MOUNT_PATH: logs_volume},
    timeout=3600,
    secrets=[
        modal.Secret.from_name("GITHUB_TOKEN"),
        modal.Secret.from_name("PORTKEY_API_KEY"),
    ],
)
def redo_issue_gen_remote(
    repo: str,
    language: str = "cpp",
    config: str = "configs/issue_gen/ig_v2.yaml",
    workers: int = 8,
) -> dict:
    from swesmith.issue_gen.generate import IssueGen

    volume_root = Path(LOGS_MOUNT_PATH) / language
    task_insts_dir = volume_root / "task_insts"

    task_insts_file = None
    repo_sanitized = repo.replace("/", "__")
    if task_insts_dir.exists():
        for filename in os.listdir(task_insts_dir):
            if filename == f"{repo_sanitized}.json" or (
                filename.startswith(f"{repo_sanitized}.") and filename.endswith(".json")
            ):
                task_insts_file = task_insts_dir / filename
                break

    if not task_insts_file or not task_insts_file.exists():
        return {
            "success": False,
            "repo": repo,
            "error": "No task instances file found",
        }

    local_logs = Path("/root/logs")
    local_logs.mkdir(parents=True, exist_ok=True)
    for subdir in ["task_insts", "run_validation", "issue_gen"]:
        local_subdir = local_logs / subdir
        volume_subdir = volume_root / subdir
        volume_subdir.mkdir(parents=True, exist_ok=True)
        try:
            if local_subdir.exists() or local_subdir.is_symlink():
                local_subdir.unlink()
            local_subdir.symlink_to(volume_subdir)
        except FileExistsError:
            pass

    issue_gen = IssueGen(
        dataset_path=str(task_insts_file),
        config_file=Path(config),
        workers=workers,
        redo_existing=True,
    )
    issue_gen.run()

    ig_file = task_insts_file.parent / f"{task_insts_file.stem}__ig_llm.json"
    issue_count = 0
    if ig_file.exists():
        data = json.loads(ig_file.read_text())
        issue_count = sum(
            1 for row in data if (row.get("problem_statement") or "").strip()
        )

    return {
        "success": True,
        "repo": repo,
        "task_insts_file": str(task_insts_file),
        "ig_file": str(ig_file),
        "issue_count": issue_count,
    }


@app.local_entrypoint()
def main(
    repo: str,
    language: str = "cpp",
    config: str = "configs/issue_gen/ig_v2.yaml",
    workers: int = 8,
):
    result = redo_issue_gen_remote.remote(repo, language, config, workers)
    print(json.dumps(result, indent=2))
