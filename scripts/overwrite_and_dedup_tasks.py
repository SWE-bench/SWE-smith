"""
Modal script to filter and overwrite SWE-smith datasets on Hugging Face.

This variant intentionally does NOT do task aggregation or issue generation.
It only:
- Loads a source HF dataset.
- Filters out rows with empty `problem_statement`.
- Pushes the filtered dataset to a target HF dataset, overwriting existing contents.
"""

import os

import modal
from datasets import DatasetDict, load_dataset
from huggingface_hub import create_repo

app = modal.App("swesmith-overwrite-hf")
image = modal.Image.debian_slim().pip_install("datasets", "huggingface_hub")


@app.function(
    image=image,
    secrets=[modal.Secret.from_name("john-hf-secret")],
    timeout=10800,
)
def filter_and_overwrite_remote(
    source_dataset: str = "SWE-bench/SWE-smith-ts",
    target_dataset: str = "SWE-bench/SWE-smith-ts",
    source_split: str = "train",
) -> dict:
    """Filter source_dataset for non-empty problem_statement and push to target_dataset."""
    token = os.environ.get("HF_TOKEN")
    if not token:
        return {"success": False, "error": "HF_TOKEN not found in environment"}

    print(f"Loading source dataset: {source_dataset} split={source_split}")
    ds = load_dataset(source_dataset, split=source_split)
    print(f"Source rows: {len(ds)}")

    filtered = ds.filter(
        lambda row: bool(str(row.get("problem_statement") or "").strip())
    )

    print(f"Filtered rows (non-empty problem_statement): {len(filtered)}")
    print(f"Dropped rows: {len(ds) - len(filtered)}")

    create_repo(target_dataset, repo_type="dataset", token=token, exist_ok=True)

    DatasetDict({"train": filtered}).push_to_hub(target_dataset, token=token)

    return {
        "success": True,
        "source_dataset": source_dataset,
        "target_dataset": target_dataset,
        "source_split": source_split,
        "source_rows": len(ds),
        "kept_rows": len(filtered),
        "dropped_rows": len(ds) - len(filtered),
    }


@app.local_entrypoint()
def main(
    source_dataset: str = "SWE-bench/SWE-smith-ts",
    target_dataset: str = "SWE-bench/SWE-smith-ts",
    source_split: str = "train",
    push: bool = False,
):
    if not push:
        confirm = input(
            f"Overwrite '{target_dataset}' from '{source_dataset}' ({source_split}) with non-empty problem_statement? (y/n) "
        ).lower()
        if confirm != "y":
            print("Aborting.")
            return

    print("Starting remote filter-and-overwrite...")
    result = filter_and_overwrite_remote.remote(
        source_dataset=source_dataset,
        target_dataset=target_dataset,
        source_split=source_split,
    )
    print(result)

    if not result.get("success"):
        raise RuntimeError(result.get("error", "Upload failed"))
