To see how SWE-smith compares against real world tasks (e.g. SWE-bench), we LoRA Fine-Tuned a [Qwen 2.5 32B Coder Instruct](https://github.com/QwenLM/Qwen2.5-Coder) model on 1.5k human ratings of the difficulty of real world bugs.

Given the issue text and patch associated with a task instance, the model will rate the task as "easy" (< 15 min), "medium" (15 min - 1 hour), or "hard" (1+ hours).

## Inference

You can rate the difficulty of your own task instances by following these steps:

1. Download the [HuggingFace checkpoint]().

2. Use `sglang` to serve the checkpoint. The training scripts available in the SWE-smith repository use [Modal](https://modal.com/) as a compute service for hosting inference.

```bash
N_HOURS=4 N_GPUS=4 modal run --detach swesmith/train/serve_sglang.py \
    --model-path /path/to/checkpoint \
    --served-model-name gpt-4o \
    --tokenizer-path /path/to/Qwen2.5-Coder-32B-Instruct
```

3. Run the following script:

```bash
swesmith train difficulty_rater get_difficulties \
    --base_url <URL where model is hosted> \
    --dataset_path path/to/dataset.json
```

The script will generate a `.json` file containing a mapping from each task instance to a difficulty score.
You can then compute the dataset's difficulty score as the average of all task instance scores.

## Prior Datasets

Using our model, we've assessed the difficulty of existing datasets, assigning scores of 1/5/9 to easy/medium/hard tasks.

| Dataset                | # Instances | Score  | `easy` | `med` | `hard` |
|------------------------|-------------|--------|--------|-------|--------|
| SWE-bench              | 2294        | 5.014  | 438    | 1408  | 446    |
| └── Lite               | 300         | 3.893  | 93     | 197   | 10     |
| └── Verified           | 500         | 3.960  | 173    | 284   | 43     |
| SWE-bench Multimodal   | 510         | 6.036  | 55     | 265   | 186    |
| SWE-gym                | 2438        | 5.625  | 288    | 1456  | 664    |
| └── Lite               | 230         | 3.890  | 67     | 156   | 4      |
| SWE-smith (LM Modify)  | 1000        | 3.304  | 441    | 542   | 17     |
| SWE-smith (LM Rewrite) | 1000        | 5.272  | 68     | 796   | 136    |
| SWE-smith (Procedural) | 1000        | 3.596  | 374    | 603   | 23     |
| SWE-smith (PR Mirror)  | 1000        | 4.876  | 206    | 619   | 175    |
| SWE-smith (Combine)    | 1000        | 5.720  | 52     | 716   | 232    |

From the table, we demonstrate that SWE-smith task instances are comparable to real world tasks, and that our bug generation techniques allow for a wide range of task difficulties.