"""
Purpose: Get difficulty ratings for different bugs

Usage:
python train/difficulty_rater/get_difficulties.py --base_url <base_url> --dataset_path <dataset_path>

NOTE:
Make sure the sglang server for the difficulty rating model is running.
"""

import argparse
import json
import openai
import os

from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from swebench.harness.constants import KEY_INSTANCE_ID
from swesmith.constants import SGLANG_API_KEY
from swesmith.train.difficulty_rater.create_datasets import (
    PROMPT_SYSTEM,
    PROMPT_INSTANCE,
)
from tqdm.auto import tqdm

DIFFICULTY_SCORE = {"15 min - 1 hour": 5, "1-4 hours": 9, "<15 min fix": 1}


def process_instance(client, instance):
    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": PROMPT_SYSTEM},
                {"role": "user", "content": PROMPT_INSTANCE.format(**instance)},
            ],
            temperature=0,
            max_tokens=64,
        )
        difficulty = response.choices[0].message.content.strip()
        return {
            KEY_INSTANCE_ID: instance[KEY_INSTANCE_ID],
            "difficulty": difficulty,
        }
    except:
        return {
            KEY_INSTANCE_ID: instance[KEY_INSTANCE_ID],
            "difficulty": "error",
        }


def main(base_url, dataset_path, overwrite=False):
    client = openai.Client(base_url=f"{base_url}/v1", api_key=SGLANG_API_KEY)

    dataset = None
    if dataset_path.endswith(".json"):
        dataset = json.load(open(dataset_path))
    elif dataset_path.endswith(".jsonl"):
        dataset = [json.loads(line) for line in open(dataset_path).readlines()]

    ext = ".json" if dataset_path.endswith(".json") else ".jsonl"
    difficulties_path = dataset_path.replace(ext, "_difficulties.jsonl")

    id_to_diff = {}
    completed = []
    mode = "w"
    if os.path.exists(difficulties_path) and not overwrite:
        for line in open(difficulties_path).readlines():
            line = json.loads(line)
            id_to_diff[line[KEY_INSTANCE_ID]] = line["difficulty"]
            completed.append(line[KEY_INSTANCE_ID])
        print(f"Skipping {len(completed)} completed instances")
        dataset = [x for x in dataset if x[KEY_INSTANCE_ID] not in completed]
        mode = "a"

    print(f"Rating {len(dataset)} instances (will write to {difficulties_path})")
    num_threads = 4  # Adjust based on API rate limits
    with (
        ThreadPoolExecutor(max_workers=num_threads) as executor,
        open(difficulties_path, mode) as f,
    ):
        future_to_instance = {
            executor.submit(process_instance, client, instance): instance
            for instance in dataset
        }

        for future in tqdm(as_completed(future_to_instance), total=len(dataset)):
            result = future.result()
            if result:  # Skip None values
                f.write(json.dumps(result) + "\n")
                id_to_diff[result[KEY_INSTANCE_ID]] = result["difficulty"]

    print(f"Assessed difficulty for {len(id_to_diff)} instances")
    difficulty_dist = Counter(id_to_diff.values())
    print(difficulty_dist)
    for k in list(difficulty_dist.keys()):
        if k not in DIFFICULTY_SCORE:
            del difficulty_dist[k]
    difficulty_rating = round(
        sum(
            DIFFICULTY_SCORE[rating] * count
            for rating, count in difficulty_dist.items()
        )
        / sum(difficulty_dist.values()),
        3,
    )
    print(f"Difficulty score: {difficulty_rating}")
    print(f"Saved to {difficulties_path}")


def get_cli_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Get difficulty ratings for different bugs"
    )
    parser.add_argument(
        "--base_url", type=str, required=True, help="Base URL of the Model API"
    )
    parser.add_argument(
        "--dataset_path", type=str, required=True, help="Path to the dataset"
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Whether to overwrite existing difficulties",
    )
    return parser


def run_from_cli(args: list[str] | None = None) -> None:
    cli_parser = get_cli_parser()
    cli_args = cli_parser.parse_args(args)
    main(**vars(cli_args))


if __name__ == "__main__":
    run_from_cli()
