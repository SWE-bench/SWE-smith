"""
Purpose: Given predictions by SWE-agent, evaluate its performance (% resolved).

Usage: python -m swesmith.harness.eval \
    --dataset_path <path to dataset> \
    --predictions_path <gold / path to predictions> \
    --run_id <unique identifier for this run> \
    --max_workers <number of workers to use>
"""

import argparse
import json
import os

from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    KEY_MODEL,
    KEY_PREDICTION,
    LOG_REPORT,
    LOG_TEST_OUTPUT,
    RUN_EVALUATION_LOG_DIR,
)
from swebench.harness.docker_build import close_logger
from swebench.harness.utils import run_threadpool
from swesmith.constants import KEY_PATCH, KEY_TIMED_OUT, TIMEOUT
from swesmith.harness.grading import get_eval_report
from swesmith.harness.utils import run_patch_in_container


def run_evaluation(
    pred: dict,
    instance: dict,
    run_id: str,
    is_gold: bool = False,
    timeout: int = TIMEOUT,
) -> None:
    """
    Run per-prediction evaluation
    """
    instance_id = pred[KEY_INSTANCE_ID]
    logger, timed_out = run_patch_in_container(  # type: ignore
        instance,
        run_id,
        RUN_EVALUATION_LOG_DIR,
        patch=pred[KEY_PREDICTION],
        commit=instance["base_commit"],
        is_gold=is_gold,
        timeout=timeout,
    )

    eval_folder = RUN_EVALUATION_LOG_DIR / run_id
    report_path = eval_folder / instance_id / LOG_REPORT
    test_log_path = eval_folder / instance_id / LOG_TEST_OUTPUT

    if timed_out:
        logger.info(f"Timed out for {instance_id}.")
        with open(report_path, "w") as f:
            f.write(json.dumps({KEY_TIMED_OUT: True, "timeout": timeout}, indent=4))
        close_logger(logger)
        return

    if not test_log_path.exists():
        logger.info(f"Failed to get report for {instance_id}.")
        close_logger(logger)
        return

    # Get report from test output
    logger.info(f"Grading answer for {instance_id}...")
    eval_folder = RUN_EVALUATION_LOG_DIR / run_id
    report = get_eval_report(pred, instance, test_log_path)
    report[KEY_MODEL] = pred[KEY_MODEL]

    # Write report to report.json
    with open(report_path, "w") as f:
        f.write(json.dumps(report, indent=4))
    close_logger(logger)


def main(
    dataset_path: str,
    predictions_path: str,
    run_id: str,
    max_workers: int,
    instance_ids: list | None = None,
    report_only: bool = False,
    timeout: int = TIMEOUT,
    redo_existing: bool = False,
):
    """
    Run evaluation of predictions on SWE-smith style dataset.
    """
    assert len(run_id) > 0, "Run ID must be provided"

    # Get predictions
    predictions = None
    is_gold = False
    if predictions_path == "gold":
        is_gold = True
        predictions = {
            x[KEY_INSTANCE_ID]: {
                KEY_INSTANCE_ID: x[KEY_INSTANCE_ID],
                KEY_PREDICTION: x[KEY_PATCH],
                KEY_MODEL: "gold",
            }
            for x in json.load(open(dataset_path))
        }
        print("Using gold predictions for eval (ignoring `predictions_path` argument)")
    else:
        if predictions_path.endswith(".json"):
            predictions = json.load(open(predictions_path))
        elif predictions_path.endswith(".jsonl"):
            predictions = [json.loads(x) for x in open(predictions_path)]
            predictions = {x[KEY_INSTANCE_ID]: x for x in predictions}
        else:
            raise ValueError("Predictions must be in .json or .jsonl format")
    predictions = {
        k: v
        for k, v in predictions.items()
        if instance_ids is None or k in instance_ids
    }

    # Early terminate if no predictions
    if len(predictions) == 0:
        print("No predictions to evaluate.")
        return

    # Get dataset
    dataset = None
    if dataset_path.endswith(".json"):
        dataset = json.load(open(dataset_path))
    elif dataset_path.endswith(".jsonl"):
        dataset = [json.loads(x) for x in open(dataset_path)]
    else:
        raise ValueError("Dataset must be in .json or .jsonl format")
    dataset = {x[KEY_INSTANCE_ID]: x for x in dataset}

    # Create logging directory
    log_dir_parent = RUN_EVALUATION_LOG_DIR / run_id
    remaining = predictions.copy()
    if not redo_existing and os.path.exists(log_dir_parent):
        # Remove completed eval runs for the instance_id
        completed = 0
        for instance_id in os.listdir(log_dir_parent):
            if instance_id in remaining and os.path.exists(
                log_dir_parent / instance_id / LOG_REPORT
            ):
                del remaining[instance_id]
                completed += 1
        print(f"Found {completed} completed evaluations. Remaining: {len(remaining)}")
    log_dir_parent.mkdir(parents=True, exist_ok=True)

    payloads = list()
    for instance_id, prediction in remaining.items():
        if instance_id not in dataset:
            print(f"Instance {instance_id} not found in dataset")
            continue
        instance = dataset[instance_id]
        payloads.append(
            (
                prediction,
                instance,
                run_id,
                is_gold,
                timeout,
            )
        )

    # Run evaluations
    if report_only:
        print("Regenerating reports only (skipping eval run)")
    else:
        run_threadpool(run_evaluation, payloads, max_workers)
        print("All instances run.")

    # Get number of task instances resolved
    ids_resolved, ids_unresolved = [], []
    num_resolved = 0
    for prediction in predictions.values():
        instance_id = prediction[KEY_INSTANCE_ID]
        report_path = log_dir_parent / instance_id / LOG_REPORT
        if not report_path.exists():
            continue
        report = json.load(open(report_path))
        resolved = report.get("resolved", False)
        num_resolved += resolved
        if resolved:
            ids_resolved.append(instance_id)
        else:
            ids_unresolved.append(instance_id)

    print(f"Resolved {num_resolved}/{len(predictions)} instances.")
    with open(log_dir_parent / LOG_REPORT, "w") as f:
        json.dump(
            {
                "resolved": num_resolved,
                "unresolved": len(ids_unresolved),
                "total": len(predictions),
                "ids_resolved": ids_resolved,
                "ids_unresolved": ids_unresolved,
            },
            f,
            indent=4,
        )
    print(f"Wrote report to {log_dir_parent / LOG_REPORT}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser("Evaluate predications on SWEFT bugs")
    parser.add_argument("--dataset_path", type=str, help="Path to dataset")
    parser.add_argument("--predictions_path", type=str, help="Path to predictions")
    parser.add_argument("--run_id", type=str, help="Unique identifier for this run")
    parser.add_argument(
        "--max_workers", type=int, help="Number of workers to use", default=4
    )
    parser.add_argument(
        "--timeout", type=int, help="Timeout for each evaluation", default=TIMEOUT * 4
    )
    parser.add_argument(
        "--redo_existing",
        action="store_true",
        help="Redo completed evaluation instances",
    )
    parser.add_argument(
        "--instance_ids", type=str, help="Instance IDs to evaluate", nargs="+"
    )
    parser.add_argument(
        "--report_only", action="store_true", help="Regenerate reports only"
    )
    args = parser.parse_args()
    main(**vars(args))
