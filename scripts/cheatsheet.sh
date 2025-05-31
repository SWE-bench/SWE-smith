#!/bin/bash

# This file contains examples for how to call all scripts and functionalities provided by the SWE-smith toolkit.

## The scripts are written such that you do *not* need to have the repository installed locally (run `pip install swesmith`).
## *Although*, some scripts require config files (you can download them from the repo).

## NOTE: If you want to create repositories + task instances under your own account,
## change swesmith/constants.py:29 (the `ORG_NAME` variable) to your own account.


###### MARK: Create Environment for Repository ######

# Attempts to create a conda environment for the repo. If successfully, a
# dump of the conda environment is saved to `logs/build_images/records``
python -m swesmith.build_repo.try_install Instagram/MonkeyType configs/install_repo.sh --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84

# Download all existing SWE-smith environments
# (All images downloaded by default, but you can specify a specific repo
# from https://github.com/orgs/swesmith/repositories using `--repo`)
python -m swesmith.build_repo.download_images

# Create execution environment (Docker images) for all repositories
python -m swesmith.build_repo.create_images --repos Instagram/MonkeyType


###### MARK: Generate Candidate Task Instances ######

# This would point at "https://github.com/swesmith/Instagram__MonkeyType.70c3acf6"
repo="Instagram__MonkeyType.70c3acf6"

# LM Rewrite
python -m swesmith.bug_gen.llm.rewrite $repo \
    --model anthropic/claude-3-7-sonnet-20250219 \
    --config_file configs/bug_gen/lm_rewrite.yml \
    --n_workers 1

# LM Modify
python -m swesmith.bug_gen.llm.modify $repo \
    --n_bugs 1 \
    --model openai/gpt-4o \
    --prompt_config configs/bug_gen/lm_modify.yml

# Procedural Modifications
python -m swesmith.bug_gen.procedural.generate $repo --max_bugs 10

# Combine (Same File) - Must have validated task instances to run this script
python -m swesmith.bug_gen.combine.same_file logs/bug_gen/$repo \
    --num_patches 3 \
    --limit_per_file 15 \
    --max_combos 100

# Combine (Same Module) - Must have validated task instances to run this script
python -m swesmith.bug_gen.combine.same_module logs/bug_gen/$repo \
    --num_patches 2 \
    --limit_per_module 20 \
    --max_combos 200 \
    --depth 2

# PR Mirroring
## NOTE: `path/to/task_candidates.jsonl` is the output of running this
## the SWE-bench task candidate collection script:
## https://github.com/SWE-bench/SWE-bench/blob/main/swebench/collect/run_get_tasks_pipeline.sh
python -m swesmith.bug_gen.mirror.generate path/to/task_candidates.jsonl --model openai/o3-mini


###### MARK: Validate + Evaluate Task Instances ######
## NOTE: Before running the below, make sure
## - You have created task instances
## - The repository you're creating task instances for has an environment (Docker image)
## - (If testing is not pytest) You've specified a log parser in swesmith/harness/log_parsers.py

# Collect all patches
python -m swesmith.bug_gen.collect_patches logs/bug_gen/$repo

# Run validation
python -m swesmith.harness.valid logs/bug_gen/$repo_all_patches.json \
    --run_id $repo

# Collect task instances with 1+ F2P
python -m swesmith.harness.gather logs/run_validation/$repo

# Run evaluation
python -m swesmith.harness.eval \
    --dataset_path logs/task_insts/$repo.json \
    --predictions_path gold \
    --run_id $repo


####### MARK: Generate Issues ######
python -m swesmith.issue_gen.generate logs/task_insts/$repo.json \
    --config_file configs/issue_gen/ig_v2.yaml \
    --model anthropic/claude-3-7-sonnet-20250219 \
    --n_workers 4 \
    --experiment_id ig_v2 \
    --use_existing

# Alternatives:
# python -m swesmith.issue_gen.get_from_pr logs/task_insts/$repo.json
# python -m swesmith.issue_gen.get_from_tests logs/task_insts/$repo.json
# python -m swesmith.issue_gen.get_static logs/task_insts/$repo.json