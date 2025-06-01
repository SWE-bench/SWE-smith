"""
Purpose: Given a repository, generate bug patches for functions/classes/objects in the repository.

Usage: python -m swesmith.bug_gen.llm.modify \
    --n_bugs <n_bugs> \
    --config_file <config_file> \
    --model <model> \
    repo  # e.g., tkrajina__gpxpy.09fc46b3

Where model follows the litellm format.

Example:

python -m swesmith.bug_gen.llm.modify tkrajina__gpxpy.09fc46b3 --config_file configs/bug_gen/class_basic.yml --model claude-3-7-sonnet-20250219 --n_bugs 1
"""

import argparse
import shutil
import jinja2
import json
import litellm
import logging
import os
import random
import yaml

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import asdict
from dotenv import load_dotenv
from litellm import completion
from litellm.cost_calculator import completion_cost
from swesmith.bug_gen.llm.utils import PROMPT_KEYS, extract_code_block
from swesmith.bug_gen.utils import (
    apply_code_change,
    extract_entities_from_directory,
    get_patch,
)
from swesmith.constants import (
    LOG_DIR_BUG_GEN,
    ORG_NAME,
    PREFIX_BUG,
    PREFIX_METADATA,
)
from swesmith.utils import BugRewrite, CodeEntity, clone_repo, repo_exists
from tqdm.auto import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from typing import Any


load_dotenv(dotenv_path=os.getenv("SWEFT_DOTENV_PATH"))

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
litellm.suppress_debug_info = True


def gen_bug_from_code_lm(
    candidate: CodeEntity, configs: dict, n_bugs: int, model: str
) -> list[BugRewrite]:
    """
    Given the source code of a function, return `n` bugs with an LM
    """

    def format_prompt(prompt: str | None, config: dict, candidate: CodeEntity) -> str:
        if not prompt:
            return ""
        env = jinja2.Environment()

        def jinja_shuffle(seq):
            result = list(seq)
            random.shuffle(result)
            return result

        env.filters["shuffle"] = jinja_shuffle
        template = env.from_string(prompt)
        return template.render(**asdict(candidate), **config.get("parameters", {}))

    def get_role(key: str) -> str:
        if key == "system":
            return "system"
        return "user"

    bugs = []
    messages = [
        {"content": format_prompt(configs[k], configs, candidate), "role": get_role(k)}
        for k in PROMPT_KEYS
    ]
    # Remove empty messages
    messages = [x for x in messages if x["content"]]
    response: Any = completion(model=model, messages=messages, n=n_bugs, temperature=1)
    for choice in response.choices:
        message = choice.message
        explanation = (
            message.content.split("Explanation:")[-1].strip()
            if "Explanation" in message.content
            else message.content.split("```")[-1].strip()
        )
        bugs.append(
            BugRewrite(
                rewrite=extract_code_block(message.content),
                explanation=explanation,
                cost=completion_cost(completion_response=response) / n_bugs,
                output=message.content,
                strategy="llm",
            )
        )
    return bugs


def main(
    config_file: str,
    model: str,
    n_bugs: int,
    repo: str,
    n_workers: int = 1,
    org: str = ORG_NAME,
    **kwargs,
):
    # Check arguments
    assert repo_exists(repo, org), f"Repository {repo} does not exist in {org}."
    assert os.path.exists(config_file), f"{config_file} not found"
    assert n_bugs > 0, "n_bugs must be greater than 0"
    configs = yaml.safe_load(open(config_file))
    assert all(key in configs for key in PROMPT_KEYS + ["criteria", "name"]), (
        f"Missing keys in {config_file}"
    )

    # Clone repository, identify valid candidates
    print("Cloning repository...")
    clone_repo(repo)
    print("Extracting candidates...")
    candidates = extract_entities_from_directory(repo)
    print(f"{len(candidates)} candidates found in {repo}")
    if not candidates:
        print(f"No candidates found in {repo}.")
        return

    print(f"Generating bugs in {repo} using {model}...")
    if not kwargs.get("yes", False):
        if input("Proceed with bug generation? (y/n): ").lower() != "y":
            return

    # Set up logging
    log_dir = LOG_DIR_BUG_GEN / repo
    log_dir.mkdir(parents=True, exist_ok=True)
    print(f"Logging bugs to {log_dir}")

    def _process_candidate(candidate: CodeEntity):
        # Run bug generation
        bugs = gen_bug_from_code_lm(candidate, configs, n_bugs, model)
        cost, n_bugs_generated, n_generation_failed = sum([x.cost for x in bugs]), 0, 0

        for bug in bugs:
            # Create artifacts
            bug_dir = log_dir / candidate.file_path.replace("/", "__") / candidate.name
            bug_dir.mkdir(parents=True, exist_ok=True)
            uuid_str = f"{configs['name']}__{bug.get_hash()}"
            metadata_path = f"{PREFIX_METADATA}__{uuid_str}.json"
            bug_path = f"{PREFIX_BUG}__{uuid_str}.diff"

            try:
                with open(bug_dir / metadata_path, "w") as f:
                    json.dump(bug.to_dict(), f, indent=2)
                apply_code_change(candidate, bug)
                patch = get_patch(repo, reset_changes=True)
                if not patch:
                    raise ValueError("Patch is empty.")
                with open(bug_dir / bug_path, "w") as f:
                    f.write(patch)
            except Exception as e:
                print(
                    f"Error applying bug to {candidate.name} in {candidate.file_path}: {e}",
                )
                # import traceback
                # print(f"Traceback:\n{''.join(traceback.format_exc())}")
                (bug_dir / metadata_path).unlink(missing_ok=True)
                n_generation_failed += 1
                continue
            else:
                n_bugs_generated += 1
        return {
            "cost": cost,
            "n_bugs_generated": n_bugs_generated,
            "n_generation_failed": n_generation_failed,
        }

    stats = {"cost": 0.0, "n_bugs_generated": 0, "n_generation_failed": 0}
    with ThreadPoolExecutor(max_workers=n_workers) as executor:
        futures = [
            executor.submit(_process_candidate, candidate) for candidate in candidates
        ]

        with logging_redirect_tqdm():
            with tqdm(total=len(candidates), desc="Candidates") as pbar:
                for future in as_completed(futures):
                    cost = future.result()
                    for k, v in cost.items():
                        stats[k] += v
                    pbar.set_postfix(stats, refresh=True)
                    pbar.update(1)

    shutil.rmtree(repo)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "repo",
        type=str,
        help="Name of a SWE-smith repository to generate bugs for.",
    )
    parser.add_argument(
        "--config_file",
        type=str,
        help="Configuration file containing bug gen. strategy prompts",
        required=True,
    )
    parser.add_argument(
        "--model",
        type=str,
        help="Model to use for bug generation",
        default="openai/gpt-4o",
    )
    parser.add_argument(
        "--n_bugs",
        type=int,
        help="Number of bugs to generate per entity",
        default=1,
    )
    parser.add_argument(
        "--n_workers", type=int, help="Number of workers to use", default=1
    )
    parser.add_argument(
        "--org",
        type=str,
        help="Organization name (default: SWE-smith)",
        default=ORG_NAME,
    )
    parser.add_argument("-y", "--yes", action="store_true", help="Skip confirmation")
    args = parser.parse_args()
    main(**vars(args))
