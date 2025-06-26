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

SWE-smith is a toolkit for training software engineering (SWE) agents. With SWE-smith, you can:
* Create an *unlimited* number of [SWE-bench](https://github.com/SWE-bench/SWE-bench) style task instances for any Python repository.
* *Generate trajectories* of [SWE-agent](https://github.com/SWE-agent/SWE-agent) solving those task instances.
* *Train local LMs* on these trajectories to improve their software engineering capabilities ([SWE-agent-LM-32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B)).

## 🚀 Get Started
Check out the [documentation](https://swesmith.com/getting_started/) for a complete guide on how to use SWE-smith, including how to
* [Install](https://swesmith.com/getting_started/installation/) the repository locally or as a PyPI package.
* [Create Task Instances](https://swesmith.com/guides/create_instances/) for any Python repository with SWE-smith.
* Use your task instance to [train your own SWE-agents](https://swesmith.com/guides/train_swe_agent/)

## 🏎️ Quick Start
Install the repo:
```bash
git clone https://github.com/SWE-bench/SWE-smith
cd SWE-smith
conda create -n smith python=3.10;
conda activate smith;
pip install -e .
```

Then, check out `scripts/cheatsheet.sh` for scripts to (1) create execution environments, (2) create task instances, and (3) train SWE-agents.

> [!TIP]
> SWE-smith requires Docker to create execution environments. SWE-smith was developed and tested on Ubuntu 22.04.4 LTS.
> We do *not* plan on supporting Windows or MacOS.

## 💿 Resources
In addition to this toolkit, we've also provided several artifacts on the [SWE-bench HuggingFace](https://huggingface.co/SWE-bench), including:
* [50k Python Task Instances](https://huggingface.co/datasets/SWE-bench/SWE-smith), created using SWE-smith.
* [SWE-agent-LM-32B](https://huggingface.co/SWE-bench/SWE-agent-LM-32B), trained using SWE-smith. Achieves **41.6%** pass@1 on [SWE-bench Verified](https://huggingface.co/datasets/SWE-bench/SWE-bench_Verified)!
* [5k Trajectories](https://huggingface.co/datasets/SWE-bench/SWE-smith-trajectories) that SWE-agent-LM-32B was trained on.

And there's more coming!

## 💫 Contributions
Excited about SWE-smith? We're actively working on several follow ups, and love meaningful collaborations! What we're thinking about...
* Make SWE-smith work for non-Python languages
* New bug generation techniques
* Train SWE-agents with more trajectories and new methods

Check out the [Contributing Guide](CONTRIBUTING.md) for more.

Contact Person: [John Yang](https://john-b-yang.github.io/), [Kilian Lieret](https://lieret.net)
(Email: [johnby@stanford.edu](mailto:johnby@stanford.edu))

## 🪪 License
MIT. Check `LICENSE` for more information.

## ✍️ Citation

```bibtex
@misc{yang2025swesmith,
  title={SWE-smith: Scaling Data for Software Engineering Agents}, 
  author={John Yang and Kilian Leret and Carlos E. Jimenez and Alexander Wettig and Kabir Khandpur and Yanzhe Zhang and Binyuan Hui and Ofir Press and Ludwig Schmidt and Diyi Yang},
  year={2025},
  eprint={2504.21798},
  archivePrefix={arXiv},
  primaryClass={cs.SE},
  url={https://arxiv.org/abs/2504.21798}, 
}
```

## 📕 Our Other Projects:
<div align="center">
  <a href="https://github.com/SWE-bench/SWE-bench"><img src="docs/assets/swebench_logo_text_below.svg" alt="SWE-bench" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-agent/SWE-agent"><img src="docs/assets/sweagent_logo_text_below.svg" alt="SWE-agent" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-agent/SWE-ReX"><img src="docs/assets/swerex_logo_text_below.svg" alt="SWE-ReX" height="120px"></a>
  &nbsp;&nbsp;
  <a href="https://github.com/SWE-bench/sb-cli"><img src="docs/assets/sbcli_logo_text_below.svg" alt="sb-cli" height="120px"></a>
</div>
