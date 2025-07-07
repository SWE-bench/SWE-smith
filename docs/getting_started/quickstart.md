We recommend checking out the [tutorials](../guides/index.md) for comprehensive guidance on SWE-smith usage.

However, if you learn more easily by playing with the code, here's sequences of scripts corresponding to different SWE-smith workflows.
If you run into issues, please consult the [tutorials](../guides/index.md) first, then open an [issue](https://github.com/SWE-bench/SWE-smith/issues/new/choose) if you can't find a solution.

### Creating Task Instances
```bash
# Run LM rewrite strategy to produce bugs
python -m swesmith.bug_gen.llm.modify pandas-dev__pandas.95280573 \
    --config_file configs/bug_gen/lm_modify.yml \
    --model claude-3-7-sonnet-20250219 \
    --n_bugs 1 \
    --n_workers=20

# Collect all task instances into a single file for validation
python -m swesmith.bug_gen.collect_patches logs/bug_gen/pandas-dev__pandas.95280573/

# Run validation on the collected task instances
python -m swesmith.harness.valid logs/bug_gen/pandas-dev__pandas.95280573_all_patches.json --workers 8

# Gather valid task instances
python -m swesmith.harness.gather logs/run_validation/pandas_test

# Generate issues for the valid task instances
python -m swesmith.issue_gen.generate \
    --dataset_path logs/run_validation/basic/pandas_test.json \
  --model claude-3-7-sonnet-20250219 \
  --n_workers=1 \
  --config_file configs/issue_gen/ig_v2.yaml \
  --experiment_id ig_v2
```

!!! tip "Next steps"

    We provide [detailed tutorials](../guides/index.md) on each of these steps.