# Assets

In addition to the paper and codebase, we release the following assets created with SWE-smith:

1. **Environments for 128 GitHub repositories.** You can download the environments (Docker images) locally by running the following command from the root directory of SWE-smith:
```bash
swesmith build_repo download_images
```

2. **SWE-smith dataset of 50k+ task instances**, made available as a [HuggingFace dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith).

3. **5k expert trajectories** + **SWE-agent-LM-32B**.
To create `SWE-agent-LM-32B`, we fine-tuned [Qwen 2.5 Coder Instruct 32B]() on the 5k trajectories.
`SWE-agent-LM-32B` achieves 40.2% pass@1 on SWE-bench Verified.
The trajectories are uploaded to a [HuggingFace dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories).
We also release the [32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B) and [7B](https://huggingface.co/SWE-bench/SWE-agent-LM-7B) versions of the model.

4. **SWE-Rater-32B**, a Qwen 2.5 Coder Instruct 32B model fine-tuned on human annotated ratings of a SWE-bench task instance's difficulty.
We release it as a [HuggingFace model](https://huggingface.co/SWE-bench/SWE-Rater-32B).