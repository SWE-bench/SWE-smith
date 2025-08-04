<p align="center">
  <a href="https://swesmith.com/">
    <img src="docs/assets/banner.png" style="height: 10em" alt="Kawhi the SWE-smith" />
  </a>
</p>

<br>

<div align="center">
<a href="https://www.python.org/">
  <img alt="Build" src="https://img.shields.io/badge/Python-3.10+-1f425f.svg?color=purple">
</a>
<a href="https://copyright.princeton.edu/policy">
  <img alt="License" src="https://img.shields.io/badge/License-MIT-blue">
</a>
<a href="https://badge.fury.io/py/swesmith">
  <img src="https://badge.fury.io/py/swesmith.svg">
</a>
<a href="https://arxiv.org/abs/2504.21798">
  <img src="https://img.shields.io/badge/arXiv-2504.21798-b31b1b.svg">
</a>
</div>

<hr />

SWE-smith is a toolkit for training [SWE-agents](https://github.com/SWE-agent/SWE-agent). You can:
* Turn any Github repository into a [SWE-gym](https://github.com/SWE-Gym/SWE-Gym).
* Create *unlimited* tasks (e.g., file localization, program repair, [SWE-bench](https://github.com/SWE-bench/SWE-bench)) for that repo.
* Train an LM to become a better SWE ([SWE-agent-LM-32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B)).

## ⚒️ Build Environments
If you're interested in turning a GitHub repository into a SWE-gym, install the package from [source](https://swesmith.com/getting_started/installation/).

> [!TIP]
> SWE-smith requires Docker to create execution environments. SWE-smith was developed and tested on Ubuntu 22.04.4 LTS.
> We do *not* plan on supporting Windows or MacOS.

You can then build a dataset for the repository by...
1. [Creating an environment](https://swesmith.com/guides/env_construction/#create-an-execution-environment)
2. [Synthesizing task instances](https://swesmith.com/guides/create_instances/)
3. [Keep tasks that break 1+ unit tests](https://swesmith.com/guides/harnesses/)
4. [Generating issue text for your tasks](https://swesmith.com/guides/issue_gen/)

## 🏋️ Train SWE-agent's
Training SWE-agent's using the [SWE-smith dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith) is super simple.
```python
from swesmith.profiles import registry
from datasets import load_dataset
ds = load_dataset("SWE-bench/SWE-smith", split="train") # Loads all 52k task instances
for task in ds:
    rp = registry.get_from_inst(task)  # Get the RepoProfile for the task
    container = rp.get_container(task) # Returns pointer to a Docker container with the task initialized

    """TODO: Train!"""
```

SWE-smith has been used to
* Fine-tune Qwen 2.5 Coder into SWE-agent-LM-32B (A +32% jump on SWE-bench Verified!) using [SWE-agent](https://github.com/SWE-agent/SWE-agent) [[Tutorial](https://swesmith.com/guides/train_swe_agent/)]
* Perform GRPO style reinforcement learning using [SkyRL](https://github.com/NovaSky-AI/SkyRL)

## 💿 Resources
* [52k Task Instances](https://huggingface.co/datasets/SWE-bench/SWE-smith)
* [SWE-agent-LM-32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B); **40.2%** pass@1 on [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)!
* [26k SWE-agent Trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories), including the 5k SWE-agent-LM-32B was trained on.
* [250+ Environments](https://github.com/SWE-bench/SWE-smith-envs), one Docker image per repo represented in SWE-smith.

And there's more coming!

## 💫 Contributions
We're actively working on several follow ups!
Check out the [Contributing Guide](CONTRIBUTING.md) for more.

Contact Person: [John Yang](https://john-b-yang.github.io/), [Kilian Lieret](https://lieret.net)
(Email: [johnby@stanford.edu](mailto:johnby@stanford.edu))

## 🪪 License
CC-BY-4.0. Check `LICENSE` for more information.

## ✍️ Citation

```bibtex
@misc{yang2025swesmith,
  title={SWE-smith: Scaling Data for Software Engineering Agents}, 
  author={John Yang and Kilian Lieret and Carlos E. Jimenez and Alexander Wettig and Kabir Khandpur and Yanzhe Zhang and Binyuan Hui and Ofir Press and Ludwig Schmidt and Diyi Yang},
  year={2025},
  eprint={2504.21798},
  archivePrefix={arXiv},
  primaryClass={cs.SE},
  url={https://arxiv.org/abs/2504.21798}, 
}
```

## 📕 Our Other Projects
<div align="center">
  <a href="https://github.com/SWE-bench/SWE-bench"><img src="docs/assets/swebench_logo_text_below.svg" alt="SWE-bench" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-agent/SWE-agent"><img src="docs/assets/sweagent_logo_text_below.svg" alt="SWE-agent" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-agent/Mini-SWE-Agent"><img src="docs/assets/mini_logo_text_below.svg" alt="Mini-SWE-Agent" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-agent/SWE-ReX"><img src="docs/assets/swerex_logo_text_below.svg" alt="SWE-ReX" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-bench/sb-cli"><img src="docs/assets/sbcli_logo_text_below.svg" alt="sb-cli" height="120px"></a>
</div>
