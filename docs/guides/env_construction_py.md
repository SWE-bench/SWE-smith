# Python Environment Options

This guide covers Python-specific options for customizing repository installation when using `try_install_py`.

## Quickstart
The following is a quick demonstration for how to use the `try_install_py` script.
For more details, refer to the "Running Example" section.

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84
```
where `install_repo.sh` is the script that installs the repository.
([Example](https://github.com/SWE-bench/SWE-smith/blob/main/configs/install_repo.sh))

If successful, two artifacts will be produced under `logs/build_repo/env/<org>__<repo>.<hash>`:

* `sweenv_[repo + commit].yml`: A dump of the conda environment that was created.
* `sweenv_[repo + commit].sh`: A log of the installation process.

## Walkthrough

Throughout this guide, we'll use the [Instagram/MonkeyType](https://github.com/Instagram/MonkeyType/) repository at commit [`70c3acf`](https://github.com/Instagram/MonkeyType/tree/70c3acf62950be5dfb28743c7a719bfdecebcd84) as our running example.

### Python Version Selection

By default, the installation script creates a conda environment with Python 3.10. You can specify a different Python version using the `--python-version` flag:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --python-version 3.11
```

This sets the `SWESMITH_PYTHON_VERSION` environment variable, which the install script uses when creating the conda environment:

```bash
conda create -n testbed "python=${PYTHON_VERSION}" -yq
```

### Test Dependency Installation

The install script now tries multiple strategies to install test dependencies, in order:

1. **Extras**: `pip install -e ".[test]"`
2. **Requirements file**: `pip install -r requirements-test.txt`
3. **Profile hooks**: Custom install commands from the repository profile

For MonkeyType, the install script will successfully use the extras approach since `setup.py` defines test dependencies in `extras_require`.

**Adding Extra Test Dependencies.** If a repository needs additional test utilities beyond its declared dependencies, use `--extra-test-deps`:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --extra-test-deps "hypothesis coverage"
```

This passes the packages to the install script via `SWESMITH_EXTRA_TEST_DEPS`, which installs them after the main test dependencies:

```bash
python -m pip install hypothesis coverage
```

### Smoke Testing

After installation, the script runs a smoke test to verify the environment works correctly.
This flag is not necessary, but provided to enable easy checking.
In general, we encourage putting all necessary installation steps in `install_repo.sh`.

**Default Behavior.** If pytest is available in the environment, the default smoke test is:
```bash
pytest -q --maxfail=1
```

For MonkeyType, this would run:
```bash
> Running smoke test: pytest -q --maxfail=1
> Smoke test passed
```

**Custom Smoke Test.** You can specify a custom smoke test command:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --smoke-cmd "python -m pytest tests/test_cli.py -v"
```

**Skipping Smoke Test.** To skip the smoke test entirely:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --skip-smoke
```

### Debugging Options

**Force Overwrite.** If the environment file already exists, you'll be prompted to overwrite it. Use `--force` to skip the prompt:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --force
```

**Keep Environments for Inspection.** By default, the script cleans up the cloned repository and conda environment after completion. Use `--no_cleanup` to keep them for debugging:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --no_cleanup
```

After running with this flag, you can inspect the environment:

```bash
conda activate testbed
cd MonkeyType
pytest tests/
```

### Complete Example

Here's a complete example using MonkeyType with multiple options:

```bash
python -m swesmith.build_repo.try_install_py Instagram/MonkeyType configs/install_repo.sh \
    --commit 70c3acf62950be5dfb28743c7a719bfdecebcd84 \
    --python-version 3.11 \
    --extra-test-deps "hypothesis" \
    --smoke-cmd "pytest tests/test_cli.py -q" \
    --force
```

This will:
- Clone MonkeyType at commit `70c3acf`
- Create a conda environment with Python 3.11
- Install the repository in editable mode
- Install test dependencies (found via `[test]` extras)
- Install `hypothesis` as an additional test dependency
- Run `pytest tests/test_cli.py -q` as the smoke test
- Force overwrite any existing environment file
- Clean up the repository and environment after completion
