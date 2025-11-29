# Create Astroid Task Instance

This plan outlines the steps to create a new task instance for `pylint-dev/astroid` mirroring PR #2496, validate it, and finalize it with the corresponding issue text.

## 1. Preparation

- **Docker Image**: Ensure the Docker image for `pylint-dev/astroid` (commit `b114f6b5`) is available.
    - We have already pulled `jyangballin/swesmith.x86_64.pylint-dev_1776_astroid.b114f6b5`.
    - **Location**: This image is stored in the local Docker daemon's registry, accessible via the tag `jyangballin/swesmith.x86_64.pylint-dev_1776_astroid.b114f6b5`.
- **Fetch Data**:
    - Download the patch for PR #2496 from GitHub (`https://github.com/pylint-dev/astroid/pull/2496.diff`).
    - Extract the issue description from Issue #2492.

## 2. Input Creation

- **Parse Patch**: Separate the PR patch into `patch` (solution) and `test_patch` (reproduction).
    - **Method**: Use a Python script with `unidiff` to parse the diff. Files containing "test", "tests", "e2e", or "testing" in their path will be assigned to `test_patch`; others to `patch`.
    - Before proceeding, validate that the PR patch has been successfully separated into patch and test_patch. do this by testing that the golden solution fails the test coverage from the test_patch and then subsequently passes after applying the solution patch.
- **Create Input File**: Generate a JSONL file (`pr_2496.jsonl`) formatted for `swesmith.bug_gen.mirror.generate`, containing:
    - `repo`: `pylint-dev/astroid`
    - `pull_number`: 2496
    - `instance_id`: `pylint-dev__astroid-2496`
    - `patch`: The solution code diff.
    - `test_patch`: The test code diff.
    - `base_commit`: The base commit of the PR (or the profile commit `b114f6b5` if appropriate).

## 3. Task Generation (PR Mirroring)

- **Run Generation**: Execute the mirroring script to create the task instance.
    ```bash
    python -m swesmith.bug_gen.mirror.generate pr_2496.jsonl --model openai/gpt-5.1
    ```

    - This will attempt to revert the PR changes on the `b114f6b5` commit, using the LLM to resolve conflicts if files have changed.

## 4. Validation

- **Run Validation**: Verify that the generated bug (reverted state) fails the tests and the reference solution passes them.
    ```bash
    python swesmith/harness/valid.py logs/bug_gen/pylint-dev/astroid/pr_mirror/pylint-dev__astroid-2496
    ```


## 5. Collection & Issue Text

- **Collect Instance**: Run `gather.py` to package the validated task into `logs/task_insts/`.
    ```bash
    python swesmith/harness/gather.py logs/run_validation/pylint-dev__astroid-2496
    ```

- **Add Issue Text**: Manually update the generated task instance JSON in `logs/task_insts/` to include the `problem_statement` derived from Issue #2492.

## 6. Evaluation

- **Run Evaluation**: specific check to ensure the task is solvable with the gold patch.
    ```bash
    python swesmith/harness/eval.py --run_id eval_astroid_2496 --predictions_path gold --instance_ids pylint-dev__astroid-2496
    ```

### To-dos

- [ ] Fetch PR #2496 diff and Issue #2492 text
- [ ] Create `pr_2496.jsonl` input file
- [ ] Run `swesmith.bug_gen.mirror.generate`
- [ ] Run validation (`valid.py`)
- [ ] Run collection (`gather.py`) and add issue text
- [ ] Run evaluation (`eval.py`)

