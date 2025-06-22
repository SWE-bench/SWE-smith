SWE-smith enables automatic construction of execution environments for repositories.
We'll review the two steps of this process:

1. SWE-agent + LM attempts to install a repository + run the testing suite.
2. Construct an execution environment (Docker image).

For this section, we'll use the [Instagram/MonkeyType](https://github.com/Instagram/MonkeyType/) repository as a running example, 
specifically at commit [`70c3acf`](https://github.com/Instagram/MonkeyType/tree/70c3acf62950be5dfb28743c7a719bfdecebcd84).

## Automatically Install Repos with SWE-agent

Coming soon!

## Create an Execution Environment
First, create the conda environment for the target repository.
```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84
```
where `install_repo.sh` is the script that installs the repository.
([Example](https://github.com/SWE-bench/SWE-smith/blob/main/configs/install_repo.sh))

If successful, two artifacts will be produced under `logs/build_repo/records/`:
* `sweenv_[repo + commit].yml`: A dump of the conda environment that was created.
* `sweenv_[repo + commit].sh`: A log of the installation process.

Next, run the following command to create a Docker image for the repository.

```bash
python -m swesmith.build_repo.create_images --repos Instagram/MonkeyType
```

This command will create two artifacts:
1. A mirror of the original repository at the specified commit, created under [`swesmith`](https://github.com/orgs/swesmith/repositories). To change the organization, you can...
    * Pass in an `--org` argument, or
    * (If built from source) Change `ORG_NAME_GH` in `swesmith/constants.py`
2. A Docker image (`swesmith.x86_64.<repo>.<commit>`) which contains the installed codebase.

It's good practice to check that your Docker image works as expected.
```bash
docker run -it --rm swesmith.x86_64.instagram__monkeytype.70c3acf6
```
Within the container, run the testing suite (e.g. `pytest`) to ensure that the codebase is functioning as expected.

!!! note "Get existing Docker images"

    All repositories represented in the SWE-smith [dataset](https://huggingface.co/datasets/SWE-bench/SWE-smith) are available to download. Simply run:
    ```bash
    python -m swesmith.build_repo.download_images
    ```
