import json
from pathlib import Path

import modal

APP_NAME = "swesmith-backfill-patchdiff"
VOLUME_NAME = "swesmith-bug-gen"
LOGS_MOUNT_PATH = "/logs"

app = modal.App(APP_NAME)
logs_volume = modal.Volume.from_name(VOLUME_NAME)


@app.function(
    timeout=3600,
    volumes={LOGS_MOUNT_PATH: logs_volume},
    max_containers=20,
)
def backfill_repo(repo_patch_file: str, language: str = "java") -> dict:
    bug_file = Path(LOGS_MOUNT_PATH) / language / "bug_gen" / repo_patch_file
    repo_id = repo_patch_file.replace("_all_patches.json", "")
    run_val_repo_dir = Path(LOGS_MOUNT_PATH) / language / "run_validation" / repo_id

    if not bug_file.exists():
        return {
            "repo_id": repo_id,
            "status": "skipped",
            "reason": "missing bug_gen file",
        }

    if not run_val_repo_dir.exists():
        return {
            "repo_id": repo_id,
            "status": "skipped",
            "reason": "missing run_validation repo dir",
        }

    try:
        patches = json.loads(bug_file.read_text())
    except Exception as e:
        return {"repo_id": repo_id, "status": "error", "error": f"parse patches: {e}"}

    eligible = 0
    written = 0
    missing_instance = 0
    missing_patch = 0

    for patch in patches:
        instance_id = patch.get("instance_id")
        if not instance_id:
            continue

        instance_dir = run_val_repo_dir / instance_id
        if not instance_dir.exists():
            missing_instance += 1
            continue

        eligible += 1
        patch_text = patch.get("patch")
        if not patch_text:
            missing_patch += 1
            continue

        (instance_dir / "patch.diff").write_text(patch_text)
        written += 1

    return {
        "repo_id": repo_id,
        "status": "ok",
        "eligible": eligible,
        "written": written,
        "missing_instance": missing_instance,
        "missing_patch": missing_patch,
    }


@app.local_entrypoint()
def main(language: str = "java"):
    entries = logs_volume.listdir(f"{language}/bug_gen")
    patch_files = [
        e.path.split("/")[-1] for e in entries if e.path.endswith("_all_patches.json")
    ]

    print(f"Found {len(patch_files)} patch files in {language}/bug_gen")

    total_eligible = 0
    total_written = 0
    total_missing_instance = 0
    total_missing_patch = 0
    ok = 0
    skipped = 0
    failed = 0

    for i, result in enumerate(
        backfill_repo.map(
            patch_files, [language] * len(patch_files), order_outputs=False
        ),
        start=1,
    ):
        status = result.get("status")
        repo_id = result.get("repo_id", "unknown")
        if status == "ok":
            ok += 1
            total_eligible += result.get("eligible", 0)
            total_written += result.get("written", 0)
            total_missing_instance += result.get("missing_instance", 0)
            total_missing_patch += result.get("missing_patch", 0)
            if i % 10 == 0 or result.get("written", 0) > 0:
                print(
                    f"[{i}/{len(patch_files)}] {repo_id}: wrote {result.get('written', 0)}"
                )
        elif status == "skipped":
            skipped += 1
        else:
            failed += 1
            print(f"[{i}/{len(patch_files)}] {repo_id}: ERROR {result.get('error')}")

    print("\nBackfill summary")
    print(f"  repos_ok:           {ok}")
    print(f"  repos_skipped:      {skipped}")
    print(f"  repos_failed:       {failed}")
    print(f"  eligible_instances: {total_eligible}")
    print(f"  patchdiff_written:  {total_written}")
    print(f"  missing_instance:   {total_missing_instance}")
    print(f"  missing_patch:      {total_missing_patch}")
