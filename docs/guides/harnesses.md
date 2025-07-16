# Validation & Evaluation

Great! You now have an execution environment + a bunch of candidate task instances. How do we determine which ones can be used for training?

We provide two harnesses for the purposes of:

* Validation: To check if a candidate task instance is usable (breaks 1+ existing tests).
* Evaluation: To check if the proposed solution for a task instance is correct.

The purposes of these harnesses are identical to their motivations in [SWE-bench](https://swe-bench.github.io).

## Validation
The validation harness is used to check if a candidate task instance is usable (breaks 1+ existing tests).

Once you've generated task instance candidates, follow these steps to validate them:

1. Collect the candidates

```bash
python -m swesmith.bug_gen.collect_patches logs/bug_gen/<repo>
```

This produces a `logs/bug_gen/<repo>_all_patches.json` file with all the candidate task instances.

2. Run validation

```bash
python -m swesmith.harness.valid logs/bug_gen/<repo>_all_patches.json
```

The validation harness works in two steps.
First, it runs the original repository's test suite to get the passing statuses of the existing tests.
Then, it applies each candidate task instance to the repository and runs the test suite again.
If the candidate task instance breaks 1+ existing tests, it is considered a usable task instance.

For each task instance, the validation harness produces a `logs/run_validation/<run_id>/<instance_id>` folder containing the following information:

* `eval.sh`: The sequence of test command(s) run
* `patch.diff`: The candidate task instance
* `report.json`: `FAIL_TO_PASS` and `PASS_TO_PASS` test cases
* `run_instance.log`: The full trace of running validation
* `test_output.txt`: The standard output of the test command(s)

3. Collect validated task instances

```bash
python -m swesmith.harness.gather logs/run_validation/<run_id>
```

Task instances with 1+ `FAIL_TO_PASS` test cases and 1+ `PASS_TO_PASS` test cases are considered valid.

This script performs two actions:

* It collects all valid task instances into a `logs/task_insts/<run_id>.json`. Each instance contains the following information:
```json
{
    "instance_id": <instance_id>,
    "repo": <repo>,
    "patch": <The diff that, when applied, creates the bug>,
    "FAIL_TO_PASS": <List of broken test cases>,
    "PASS_TO_PASS": <List of passing test cases>,
    "image_name": <docker image name>,
}
```
* For each valid task instance, a branch called `<instance_id>` is created in the repository. The branch corresponds to the repository with the task instance's bug patch applied.

## Evaluation

The evaluation harness is used to check if the proposed solution for a task instance is correct.

You can run this script to sanity check that testing for validated task instances works as expected:

```bash
python -m swesmith.harness.eval \
    --dataset_path bugs/task_insts/{repo}.json \
    --predictions_path gold \
    --run_id sanity
```

If you want to run on real predictions, simply replace `gold` with the path to your predictions, which should look like:

```json
{
    "instance_id": <instance_id>,
    "patch": <The diff that, when applied, fixes the bug>,
    "model_name_or_path": <The model used to generate the patch>,
}
```
