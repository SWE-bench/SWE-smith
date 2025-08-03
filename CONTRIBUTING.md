# Contributing
Updated 7/21/2025

Thanks for your interest!
First, make sure to [install](https://swesmith.com/getting_started/installation/) SWE-smith, which should be super easy!
Then, there's several ways to contribute.

* Add support for new languages
* Add repositories
* Add task instances
* Add problem statements

Each of these is described in more detail below. The priority level is indicated as
* 🔴 `p1` - High priority. We'd love help here!
* 🟠 `p2` - Medium priority
* 🟡 `p3` - Low priority

<hr />

## Support New Languages

🟡 `p3`

To generate bugs, SWE-smith relies on language-specific tooling to parse a codebase into individual programmatic entities (e.g., functions, classes, methods).
These tools are located under the `swesmith/bug_gen/adapters` folder.

We warmly welcome contributions to support new languages! [#111](https://github.com/SWE-bench/SWE-smith/pull/111), [#84](https://github.com/SWE-bench/SWE-smith/pull/84), [#66](https://github.com/SWE-bench/SWE-smith/pull/66), [#60](https://github.com/SWE-bench/SWE-smith/pull/60), [#34](https://github.com/SWE-bench/SWE-smith/pull/34), and [#28](https://github.com/SWE-bench/SWE-smith/pull/28) are great references for PRs that added support for a new language.

The best way to undestand this is by looking at the PRs and existing adapters, so we'll be brief here! Some languages we'd love to see:
- [ ] C++
- [ ] Kotlin
- [ ] Scala
- [ ] Swift

If you need help, open an issue and ask [@acrmp](https://github.com/acrmp), [@john-b-yang](https://github.com/john-b-yang), or [@klieret](https://github.com/klieret) for help! To contribute, make a new PR with the corresponding code.

<hr />

## Support New Repositories

🔴 `p1` (Especially non-Python repos)

The second puzzle piece to making bug generation work is providing programmatic definitions for GitHub repositories, which we refer to as `RepoProfile`'s in the codebase.
See `swesmith/profiles` for examples.

Each `RepoProfile` class corresponds to a unique GitHub repository + commit combination.
For instance, `Instagram__MonkeyType.70c3acf6` refers to the `Instagram/MonkeyType` repository at commit `70c3acf6`.
For each `RepoProfile`, you may have to fill out several fields, such as...
* `dockerfile` property: The `Dockerfile` that builds a Docker image with the repository installed.
* `test_cmd` property: The command that runs the repository's test suite.
* `log_parser` function: A function that parses the logs produced by the repository's test suite.
We've annotated `RepoProfile` in `swesmith/profiles/base.py` with docstrings to (1) help you understand the purpose of each function/property, and (2) point out which fields are required, optional, or have reasonable defaults.

Check out [#116](https://github.com/SWE-bench/SWE-smith/pull/116) and [d8b20f3f](https://github.com/SWE-bench/SWE-smith/commit/d8b20f3f2ee13e8c9b6ef9495c25e9704008d07a) for examples of PRs / commits that added new repositories.

> [!NOTE]
> You may need to populate the `eval_sets` property. See [#136](https://github.com/SWE-bench/SWE-smith/pull/136) for an explanation.
> 
> tl;dr - There's several SWE-bench style benchmarks out there. If we add a repo that's also used in one of these benchmarks, we want to indicate this in the `eval_sets` property.
> This way, if we want to train repos on a specific benchmark, we know which ones to exclude.
>
> <details>
>      <summary>⚠️ Run this check after adding repos:</summary>
>
> ```python
> from swesmith.profiles import registry
> from datasets import load_dataset
> 
> sb = set(load_dataset("SWE-bench/SWE-bench_Verified", split="test")["repo"])
> sbmm = set(load_dataset("SWE-bench/SWE-bench_Multimodal", split="test")["repo"])
> sbml = set(load_dataset("SWE-bench/SWE-bench_Multilingual", split="test")["repo"])
> 
> profiles = {
>     f"{rp.owner}/{rp.repo}": rp.eval_sets
>     for rp in registry.values()
> }
> 
> for test_repos, test_set in [
>     (sb, "SWE-bench_Verified"),
>     (sbmm, "SWE-bench_Multimodal"),
>     (sbml, "SWE-bench_Multilingual"),
> ]:
>     for repo in test_repos:
>         if repo not in profiles:
>             continue
>         if test_set not in profiles[repo]:
>             print(f"Add {test_set} to {repo}'s `eval_sets` property")
> ```
> </details>

We're always looking to add more repositories, so if you have a favorite open-source project, please consider adding it! To contribute, make a new PR with the corresponding code.

If you need help, open an issue and ask [@richardzhuang0412](https://github.com/richardzhuang0412), [@acrmp](https://github.com/acrmp), [@john-b-yang](https://github.com/john-b-yang), or [@klieret](https://github.com/klieret) for help!

<hr />

## Create task instances

🔴 `p1` (Especially non-Python repos)

Generating task instances is very easy.
* The ["Create Instances"](https://swesmith.com/guides/create_instances/) section of the SWE-smith docs describes this repository's bug generation strategies in detail.
* The [Youtube Playlist](https://youtube.com/playlist?list=PL1b-qYhmIXEhyaUafmTYmMI4l9dbCLNix&si=7xnYixLc7MJSy7UU) shows you what things should look like when you run the scripts.
* `scripts/cheatsheet.sh` contains the CLI commands to run scripts. Re-adapt these commands to a new repository, and run.

If you have any trouble running these scripts, please open an issue and ask [@john-b-yang](https://github.com/john-b-yang) or [@klieret](https://github.com/klieret) for help!
For the LM Rewrite/Modify and PR mirror methods, you'll have to initialize a `.env` file with `ANTHROPIC_API_KEY` and/or `OPENAI_API_KEY` set, depending on which LM you want to use.

To contribute task instances, run any of the `python -m swesmith.bug_gen.*` scripts. Every script will populate a `logs/bug_gen/<repo>/` folder, which will contain the generated bugs.
Zip this folder, then upload the zipped file as a new PR.
From there, we then perform the following additional steps:
* `python swesmith/harness/valid.py logs/bug_gen/<repo>_all_patches.json`, to filter out bugs that don't break any existing unit tests.
* `python swesmith/harness/eval.py logs/run_validation/<repo>`, to sanity check that the generated bugs are valid and reproducible.
* `python swesmith/harness/gather.py logs/run_validation/<repo>`, to collect the bugs into a single `logs/task_insts/<repo>.json` file and push valid bugs as branches to the corresponding repository under the [SWE-smith](https://github.com/orgs/swesmith/repositories) organization.
* Push the new bugs to the [SWE-bench/SWE-smith HF dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith) for all of us to use!

<hr />

## Add problem statements

🔴 `p1`

Currently, ~40k of the task instances in the [SWE-bench/SWE-smith HF dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith) do not have problem statements.
It costs ~$0.02 to create one.

```
python swesmith/issue_gen/generate.py -c=configs/issue_gen/ig_v2.yaml -w 8
```
If you want to add problem statements for just a specific repository, use the `--instance_ids` flag to use patterns to filter for specific task instances (e.g. `--instance_ids Instagram__MonkeyType.*`).

This command will populate a `logs/issue_gen/` folder with problem statements for all task instances that don't have one.
Zip this folder, then upload the zipped file as a new PR.
From there, we will attach the problem statements to the corresponding task instances in the [SWE-bench/SWE-smith HF dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith), and push!

<hr />

## Miscellaneous

Here are some ideas and contributions that we're not prioritizing at the moment, but if you're interested, we'd love to help you make it happen!
Open an issue indicating you're interested, and we'll help you get started.

* Make [Procedural Modification](https://swesmith.com/guides/create_instances/#procedural-modification) bug generation work for non-Python repos
* Add bug generation strategies
    * Create instances corresponding to "subtasks" of SWE-bench. E.g. file localization, patch repair.
* Add SWE-agent trajectories
* Improve test coverage
