"""
Purpose: Given a bug patch, generate a GitHub-style issue that describes the bug.

python swesmith/issue_gen/generate.py \
    --dataset logs/experiments/*.json \
    --config configs/issue_gen/*.yaml \
    --model anthropic/claude-3-7-sonnet-20250219 \
    --workers 2 \
    --redo_existing  # Optional: regenerate existing issue texts
"""

import argparse
import jinja2
import json
import litellm
import logging
import os
import random
import shutil
import yaml

from concurrent.futures import ThreadPoolExecutor, as_completed
from datasets import load_dataset
from dotenv import load_dotenv
from litellm import completion, completion_cost
from litellm.utils import get_token_count
from pathlib import Path
from tqdm import tqdm
from tqdm.contrib.logging import logging_redirect_tqdm
from swebench.harness.constants import (
    FAIL_TO_PASS,
    KEY_INSTANCE_ID,
    LOG_TEST_OUTPUT,
)
from swesmith.constants import (
    KEY_PATCH,
    HF_DATASET,
    LOG_DIR_ISSUE_GEN,
    LOG_DIR_RUN_VALIDATION,
    TEST_OUTPUT_END,
    TEST_OUTPUT_START,
)
from swesmith.harness.utils import (
    matches_instance_filter,
    run_patch_in_container,
)
from swesmith.issue_gen.utils import get_test_function
from swesmith.profiles import registry

logging.getLogger("LiteLLM").setLevel(logging.WARNING)
litellm.drop_params = True
litellm.suppress_debug_info = True


TEST_SRC_CODE_PROMPT = r"""
**Test Source Code:**
Use the following test source code to help you write reasonable, effective reproduction code.

{test_src_code}
"""

load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)


def maybe_shorten(text_str: str, max_tokens: int, model: str) -> str:
    """Shorten text if it exceeds the max_tokens limit.
    If shortening, return a string with the first and last max_tokens//2 tokens.
    """
    if get_token_count([{"content": text_str}], model) < max_tokens:
        return text_str
    return text_str[: max_tokens // 2] + "\n\n(...)\n\n" + text_str[-max_tokens // 2 :]


class IssueGen:
    def __init__(
        self,
        config_file: Path,
        workers: int,
        instance_ids: list | None = None,
        dataset_path: str = HF_DATASET,
        redo_existing: bool = False,
    ):
        self.dataset_path = dataset_path
        self.redo_existing = redo_existing
        self.workers = workers

        self.config = yaml.safe_load(config_file.read_text())
        self.model = self.config.get("model", "openai/gpt-4o")
        settings = self.config.get("settings", {})
        self.n_instructions = settings.get("n_instructions", 1)
        self.max_var_tokens = settings.get("max_var_tokens", 10_000)

        data_smith = [x for x in load_dataset(HF_DATASET, split="train")]
        self.dataset = (
            data_smith
            if dataset_path == HF_DATASET
            else json.loads(Path(dataset_path).read_text())
        )
        logger.info(f"Loaded {len(self.dataset)} instances from {dataset_path}")

        # Filter out instances that already have problem statements in HF dataset
        existing_problems = {
            d["instance_id"] for d in data_smith if d.get("problem_statement")
        }
        self.dataset = [
            x for x in self.dataset if x[KEY_INSTANCE_ID] not in existing_problems
        ]
        logger.info(
            f"Found {len(self.dataset)} instances without existing problem statements"
        )

        # Further filter based on other criteria
        self.dataset = sorted(
            [
                x
                for x in self.dataset
                if self._should_do_instance(x, instance_ids, redo_existing, self.model)
            ],
            key=lambda x: x[KEY_INSTANCE_ID],
        )
        logger.info(f"Will create issues for {len(self.dataset)} instances")

        if len(self.dataset) == 0:
            logger.warning(
                "No instances to process after filtering. Exiting gracefully."
            )
            return

        if FAIL_TO_PASS not in self.dataset[0]:
            raise ValueError(
                "Must be called with the result of swesmith.harness.gather, not the _all_patches.json file"
            )
        self.swebv = load_dataset("princeton-nlp/SWE-bench_Verified", split="test")

    def _should_do_instance(
        self, instance: dict, instance_ids: list | None, redo_existing: bool, model: str
    ) -> bool:
        repo = instance["repo"].split("/")[-1]
        output_file = LOG_DIR_ISSUE_GEN / repo / f"{instance[KEY_INSTANCE_ID]}.json"
        if not matches_instance_filter(instance[KEY_INSTANCE_ID], instance_ids):
            return False
        if redo_existing:
            return True
        if not output_file.exists():
            return True
        metadata = json.loads(output_file.read_text())
        if "responses" not in metadata:
            return True
        if model not in metadata["responses"]:
            return True
        return False

    def get_test_output(self, instance: dict) -> str:
        rp = registry.get_from_inst(instance)

        # Get execution output from running pytest for this instance (from validation step)
        test_output_path = (
            LOG_DIR_RUN_VALIDATION
            / instance["repo"].split("/")[-1]
            / instance[KEY_INSTANCE_ID]
            / LOG_TEST_OUTPUT
        )
        if not test_output_path.exists():
            run_patch_in_container(
                instance,
                instance["repo"].split("/")[-1],
                LOG_DIR_RUN_VALIDATION,
                rp.timeout,
                patch=instance[KEY_PATCH],
            )
        test_output = test_output_path.read_text()

        return maybe_shorten(
            test_output[
                test_output.find(TEST_OUTPUT_START)
                + len(TEST_OUTPUT_START) : test_output.find(TEST_OUTPUT_END)
            ],
            self.max_var_tokens,
            self.model,
        )

    def get_test_functions(self, instance: dict) -> tuple[list[str], list[str]]:
        """
        Get the source code for tests associated with the instance.

        Returns:
            list of test functions, list of repos to remove
        """
        test_funcs = []
        repos_to_remove = []
        test_idxs = list(range(len(instance[FAIL_TO_PASS])))
        random.shuffle(test_idxs)
        for test_idx in test_idxs:
            test_func = get_test_function(instance, test_idx)
            if test_func["cloned"]:
                repos_to_remove.append(test_func["repo_name"])
            test_funcs.append(test_func["test_src"])
        return test_funcs, repos_to_remove

    def get_demo_issues(self) -> list[str]:
        """
        Get a list of demonstration issues from the config file.
        """
        problem_statements = [
            maybe_shorten(instance["problem_statement"], 2000, self.model)
            for instance in self.swebv
        ]  # type: ignore[index]
        random.shuffle(problem_statements)
        return problem_statements

    def generate_issue(self, instance: dict) -> dict:
        # Set up logging information
        repo = instance["repo"].split("/")[-1]
        inst_dir = LOG_DIR_ISSUE_GEN / repo
        inst_dir.mkdir(parents=True, exist_ok=True)

        output_file = inst_dir / f"{instance[KEY_INSTANCE_ID]}.json"
        output_file_exists = output_file.exists()

        # Get a reference instance from SWE-bench
        instance_curr = instance.copy()

        def format_prompt(prompt: str | None, config: dict, candidate: dict) -> str:
            if not prompt:
                return ""
            env = jinja2.Environment()

            def jinja_shuffle(seq):
                result = list(seq)
                random.shuffle(result)
                return result

            env.filters["shuffle"] = jinja_shuffle
            template = env.from_string(prompt)
            return template.render(**candidate, **config.get("parameters", {}))

        metadata = {}
        if output_file_exists:
            metadata = json.loads(output_file.read_text())

        if "messages" not in metadata:
            # Generate prompt
            messages = [
                {"content": self.config["system"], "role": "system"},
            ]
            if self.config["demonstration"]:
                messages.append(
                    {
                        "content": format_prompt(
                            self.config["demonstration"],
                            self.config,
                            {"demo_problem_statements": self.get_demo_issues()},
                        ),
                        "role": "user",
                    },
                )
            test_funcs, repos_to_remove = self.get_test_functions(instance_curr)
            messages.append(
                {
                    "content": format_prompt(
                        self.config["instance"],
                        self.config,
                        instance_curr
                        | {
                            "test_output": self.get_test_output(instance_curr),
                            "test_funcs": test_funcs,
                        },
                    ),
                    "role": "user",
                },
            )
            metadata = {"messages": messages, "repos_to_remove": repos_to_remove}
            with open(output_file, "w") as f_:
                json.dump(metadata, f_, indent=4)
        else:
            # If messages already exist, get repos_to_remove from existing metadata
            _, repos_to_remove = self.get_test_functions(instance_curr)

        # Generate n_instructions completions containing problem statements
        response = completion(
            model=self.model, messages=messages, n=self.n_instructions, temperature=0
        )

        cost = completion_cost(response)
        metadata["cost"] = (0 if "cost" not in metadata else metadata["cost"]) + cost

        # Extract problem statements from response
        problem_statements = [
            choice.message.content  # type: ignore[attr-defined]
            for choice in response.choices  # type: ignore[attr-defined]
        ]

        if "responses" not in metadata:
            # Initialize responses dict if it doesn't exist
            metadata["responses"] = {}
        elif self.model in metadata["responses"]:
            # If responses for this model already exist, prepend them to the new ones
            problem_statements = metadata["responses"][self.model] + problem_statements

        # Add/update the response for current model
        metadata["responses"][self.model] = problem_statements

        with open(output_file, "w") as f_:
            json.dump(metadata, f_, indent=4)

        return {
            "status": "completed",
            "cost": cost,
            "repos_to_remove": repos_to_remove,
        }

    def _cleanup_repos(self, repos_to_remove):
        """Remove cloned repositories."""
        if not repos_to_remove:
            return

        logger.info(f"Cleaning up {len(repos_to_remove)} cloned repositories...")
        for repo_path in repos_to_remove:
            if os.path.exists(repo_path):
                try:
                    shutil.rmtree(repo_path)
                    logger.debug(f"Removed repository: {repo_path}")
                except Exception as e:
                    logger.warning(f"Failed to remove repository {repo_path}: {e}")
        logger.info("Repository cleanup completed.")

    def run(self):
        # Check if dataset is empty (initialization returned early)
        if not hasattr(self, "dataset") or len(self.dataset) == 0:
            logger.info("No instances to process. Exiting.")
            return

        stats = {
            "💰": 0.0,
            "⏭️": 0,
            "❌": 0,
            "✅": 0,
        }

        # Track repos to remove for cleanup
        all_repos_to_remove = set()

        # Create a thread pool and call generate_issue for each instance
        with ThreadPoolExecutor(max_workers=self.workers) as executor:
            futures = []
            for instance in self.dataset:
                future = executor.submit(self.generate_issue, instance)
                futures.append(future)

            # Wait for all futures to complete
            with logging_redirect_tqdm():
                with tqdm(total=len(futures), desc="Generating issues") as pbar:
                    for future in as_completed(futures):
                        try:
                            result = future.result()
                        except KeyboardInterrupt:
                            raise
                        except Exception as e:
                            logger.error(
                                f"Error processing instance: {e}", exc_info=True
                            )
                            stats["❌"] += 1
                            continue
                        if result["status"] == "skipped":
                            stats["⏭️"] += 1
                        elif result["status"] == "completed":
                            stats["✅"] += 1
                            stats["💰"] += result["cost"]
                            # Collect repos to remove
                            if "repos_to_remove" in result:
                                all_repos_to_remove.update(result["repos_to_remove"])
                        pbar.set_postfix(stats, refresh=True)
                        pbar.update(1)

        # Cleanup cloned repositories
        self._cleanup_repos(all_repos_to_remove)

        # Merge generated issues into task instances
        if self.dataset_path == HF_DATASET:
            return
        dataset_path = Path(self.dataset_path)
        full_dataset = json.loads(dataset_path.read_text())
        kept = []
        for instance in full_dataset:
            repo = instance["repo"].split("/")[-1]
            output_file = LOG_DIR_ISSUE_GEN / repo / f"{instance[KEY_INSTANCE_ID]}.json"
            if not output_file.exists():
                continue
            metadata = json.loads(output_file.read_text())
            if "responses" not in metadata or self.model not in metadata["responses"]:
                continue
            instance["problem_statement"] = metadata["responses"][self.model][0]
            kept.append(instance)

        if kept:
            out_path = dataset_path.parent / f"{dataset_path.stem}__ig_llm.json"
            with open(out_path, "w") as f:
                json.dump(kept, f, indent=2)
            print(
                f"Wrote {len(kept)}/{len(full_dataset)} instances with problem statements to {out_path}"
            )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-d",
        "--dataset_path",
        type=str,
        help="Path to the dataset to annotate with bugs.",
        default=HF_DATASET,
    )
    parser.add_argument(
        "-i",
        "--instance_ids",
        type=str,
        help="Instance IDs to evaluate (supports exact matches and glob patterns like 'repo__name.*')",
        nargs="+",
    )
    parser.add_argument(
        "-c", "--config_file", type=Path, help="Path to the template config file."
    )
    parser.add_argument(
        "-w",
        "--workers",
        type=int,
        help="Number of workers to use for generation.",
        default=1,
    )
    parser.add_argument(
        "-r",
        "--redo_existing",
        action="store_true",
        help="Whether to redo instances that already have an output file.",
    )
    args = parser.parse_args()
    if args.workers == 1:
        logger.warning(
            "Using only 1 worker for generation. You can speed up the generation by setting --workers > 1."
        )
    IssueGen(**vars(args)).run()
