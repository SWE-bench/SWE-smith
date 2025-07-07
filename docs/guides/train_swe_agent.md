# Training SWE-agents

Now the fun part - we provide details on how to operationalize SWE-smith for training SWE-agents!

Specifically, we'll cover the workflow for Rejection Sampling Fine Tuning.

!!! note "SWE-agent"

    The documentation in this section is heavily grounded in the [SWE-agent](https://github.com/SWE-agent/SWE-agent) library.
    We do *not* plan to explicitly support non SWE-agent scaffolds, but it should not be difficult - the main adaptations would just be how you generate expert trajectories and predictions for evaluation.

There's several steps we'll cover:

1. Creating a subset of SWE-smith task instances.
2. Generating expert trajectories for those task instances.
3. Training a model on the expert trajectories.
4. Evaluating the model on SWE-bench (Lite/Verified/Multimodal).

## Creating SWE-smith Subset

If you are using SWE-smith, the dataset of all [SWE-smith](https://huggingface.co/datasets/SWE-bench/SWE-smith) is quite large.
Usually, we recommend training on a subset.
To curate a subset, you might use the following logic.

```python
import json

from datasets import load_dataset
swesmith = load_dataset("SWE-bench/SWE-smith", split="train")

subset_name = "subset0"
def criteria(task_instance):
    return ".pr_" in task_instance["instance_id"] and \
        len(task_instance["FAIL_TO_PASS"]) <= 5 and \
        len(task_instance["FAIL_TO_PASS"]) >= 2
bugs = [x for x in swesmith if criteria(x)]
print(f"Found {len(bugs)} bugs that match criteria")
with open(f"logs/experiments/{subset_name}.json", "w") as f:
    json.dump(bugs, fp=f, indent=2)
```

## Generate Expert Trajectories

1. Clone [SWE-agent](https://github.com/SWE-agent/SWE-agent). Make sure to follow the installation instructions [here](https://swe-agent.com/latest/installation/source/).

2. Create a soft link of the `agent/` folder to SWE-agent, meaning in SWE-agent, run:
```bash
ln -s path/to/SWE-smith/agent/ .
```

3. In SWE-agent, run exeprt trajectory generation:
```bash
./agent/_gen_trajs.sh
```
Check the file to see how the script works. You'll need to adjust the `--instances.path` argument to point to the subset you created in the previous step.

## Train Model

The previous step will generate individual trajectories per task instance under the `SWE-agent/trajectories/<username>/<run ID>/` folder.

We'll now determine which trajectories correspond to resolved instances, convert them to a format that can be used for SFT, and then train a model with them.

1. (From SWE-smith) Run evaluation on training task instances.
```bash
python -m swesmith.harness.eval \
    --dataset_path path/to/subset0.json \
    --predictions_path path/to/trajectories/<username>/<run ID>/preds.json \
    --run_id <run ID> \
    --workers 10 \
    --timeout 240
```

!!! tip "`preds.json`"
    If there is no `preds.json`, run `sweagent merge-preds trajectories/<username>/<run ID>/`.

This evaluation will generate a `logs/run_evaluation/<run ID>/`
folder with a `report.json` file indicating which instance IDs were successfully resolved.

2. (From SWE-smith) Convert trajectories into SFT format.

```bash
python -m swesmith.train.traj_mgr.transform_to_ft \
    --traj_dir path/to/trajectories/<username>/<run ID>/ \
    --eval_dir logs/run_evaluation/<run ID>/ \
    --only_resolved
```

This will product an `ft_xml_*.jsonl` file under the `trajectories_sft/` folder.
This dataset can be used directly for SFT.

3. Run training. First, upload the file to Modal
```bash
modal volume put <volume> trajectories_sft/ft_xml_*.jsonl
```

Then, modify `config/train/full_ft_qwen_7b.yml` to point to the file in Modal.

Finally, run the training script:
```bash
./scripts/train.run_ft_torchtune.py
```

## Evaluation
Run inference on SWE-agent + your SFT'ed model on SWE-bench (Lite/Verified/Multimodal).

1. (From SWE-smith) Update `scripts/train.serve_sglang.sh` to point at SFT'ed model, then run it.

2. (From SWE-agent) Run inference:
```bash
./agent/_infer_model.sh
```
Make sure the Modal URL is correct and change the evaluation dataset as desired.

3. When inference finishes, run evaluation on the model's predictions. (Check out [sb-cli](https://github.com/SWE-bench/sb-cli/tree/main) for more information on how to conveniently run evaluation for SWE-bench-* datasets.)
```bash
sb-cli submit swe-bench_verified test \
    --predictions_path trajectories/<username>/<run ID>/preds.json \
    --run_id <run ID>
```