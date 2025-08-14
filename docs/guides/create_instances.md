You should now have an environment (Docker image) of a repository. Let's synthesize some task instances.

Task instances are modified versions of the codebase which break existing tests.
The formulation for these task instances is identical to the definition put forth by [SWE-bench](https://swe-bench.github.io).

!!! note "Bugs and task instances"

    The terms "bug" and "task instance" are used interchangeably in this documentation. They refer to the same thing.

We design each method with the following principles in mind:

* **Generalizability**: These methods work for any Python repository.
* **Scalability**: These methods require little to no manual intervention.
* **Diversity**: These methods generate a diverse set of bugs.

<div style="text-align:center;margin-top:1.5rem">
  <img src="../../assets/bug_gen_overview.png" alt="Bug Generation Overview" style="width:80%"/>
</div>

As input, each method takes in the name of a GitHub repository, along with method-specific flags.

As output, each method produces artifacts under `logs/bug_gen/<repo>`.
A candidate task instance is usually represented as two files:

1. A `bug__<bug_type>__<hash>.diff` file that, when applied to the repository, introduces a bug.
2. A `metadata__<bug_type>__<hash>.json` file containing metadata about how the task instance was created.

The `bug_*.diff` files are the candidate task instances.
The `<hash>` is computed over the contents of the `bug__<bug_type>__<hash>.diff` file.
The `metadata_*.json` files are created for statistical and analytical purposes.

## LM Generated

**How does it work?**
<div style="text-align:center">
  <img src="../../assets/lm_generate.png" alt="SWE-smith" style="width:100%"/>
</div>

We first identify all unique programmatic entities (e.g., classes, functions) in a repository.
Per entity, we prompt a language model to either:

* *Modify* the entity such that a bug is introduced (a.k.a. *LM Modify*) or
* *Rewrite* the entity from scratch (a.k.a. *LM Rewrite*).

**How do I run it?**
To prompt an LM to modify a function to introduce a bug:
```bash
python -m swesmith.bug_gen.llm.modify $repo \
  --n_bugs 1 \
  --model openai/gpt-4o \
  --config_file configs/bug_gen/lm_modify.yml
```

To prompt an LM to rewrite a function from scratch:
```bash
python -m swesmith.bug_gen.llm.rewrite $repo \
  --model anthropic/claude-3-7-sonnet-20250219 \
  --config_file configs/bug_gen/lm_rewrite.yml \
  --n_workers 1
```

**What artifact(s) does it produce?**
Under `logs/bug_gen/<repo>`, you will find a 2 dimensional folder structure.

* The first dimension corresponds to a file path in that repository (e.g., `<repo>__src__utils__rule_utils.py`, which
would correspond to `src/utils/rule_utils.py`).
* The second dimension corresponds to individual functions or classes in that file.

Under each of these folders, you will see:

* For LM Modify, `bug__lm_modify__<hash>.diff` + `metadata__lm_modify__<hash>.json` files
* For LM Rewrite, `bug__lm_rewrite__<hash>.diff` + `metadata__lm_rewrite__<hash>.json` files

## Procedural Modification

**How does it work?**
<div style="text-align:center">
  <img src="../../assets/procedural.png" alt="SWE-smith" style="width:100%"/>
</div>

Similar to LM Generated bugs, we first identify all unique programmatic entities in a repository.
Next, we convert every entity into an `ast` (Abstract Syntax Tree) object.

We then modify the AST.
For each programmatic entity, we check whether it satisfies a set of criteria that checks whether the entity can be modified in a certain way.
If the criteria is met, we modify the AST, then convert it back into source code.

A concrete example: We create a Procedural Modification technique that removes `if` conditional blocks from a function.
We check whether a function has an `if` block in it.
If it does, we remove the `if` subtree from the AST, then convert the modified AST back into code.

Why AST's instead of the literal code?
Because AST's give us a rigorous representation that allow modifications of specific program structures to be enforced easily and effortlessly.

**How do I run it?**
```bash
python -m swesmith.bug_gen.procedural.generate $repo \
  --max_bugs 10
```

**What artifact(s) does it produce?**
Identical to LM Generated task instances, but the artifacts are instead named:

* `bug__func_pm_<name>__<hash>.diff`, for instance `bug__func_pm_ctrl_shuffle__jdinra8l.diff`.
* `metadata__func_pm_<name>__<hash>.json`

Where `<name>` refers to the specific identifier for the procedural modification technique.
There are 13 (and counting) in total.

## PR Mirroring

**How does it work?**
<div style="text-align:center">
  <img src="../../assets/pr_mirror.png" alt="SWE-smith" style="width:100%"/>
</div>

This method leverages SWE-bench's [task collection script](https://github.com/SWE-bench/SWE-bench/blob/main/swebench/collect/run_get_tasks_pipeline.sh).

Run the script for a repository, and it will create a `<repo>-task-instances.jsonl.all`.
This file contains candidate task instances based on real pull requests (PRs) from the repository.
A pull request is considered a candidate if

* It has at least 1+ issue associated with it.
* It edits at least 1+ code file.

!!! note "Candidate criteria"
    SWE-bench has slightly more stringent criteria for PRs that qualify as candidates.
    Specifically, PRs must also change 1+ test file(s).
    Because SWE-smith does rely on test file changes to identify breaking existing tests, we can attempt to recreate a broader
    subset of PRs than what SWE-bench normally considers.

We provide this file to SWE-smith.
Per PR, we ask an LM to revert the PR's changes file by file.
If this process succeeds, we create a candidate task instance that effectively undoes the PR.

**How do I run it?**
```bash
python -m swesmith.bug_gen.mirror.generate $file \
    --model openai/o3-mini
```

**What artifact(s) does it produce?**



## Combining Bugs

**How does it work?**
<div style="text-align:center">
  <img src="../../assets/combine.png" alt="SWE-smith" style="width:100%"/>
</div>

You might have noticed that Procedural Modification and LM Generated bugs both target individual entities.
This means at most one file is modified per bug.

We can create more complex bugs by simply combining multiple bugs together.

We generally do this by identifying patches that modify the same file or module.
A module refers to subdirectories in the codebase.

For the identified patches, we apply them one by one.
If they all apply cleanly, we combine them into a single patch.

You can control

* `num_patches`: The number of patches to combine together.
* `limit_per_file/module`: Maximum number of combined bugs to generate for any file/module.
* `max_combos`: Maximum number of candidate combinations to generate.
* (For Module) `depth`: A depth of `2` means any patches under `a/b` are considered to be in the same module. A depth of `3` means any patches under `a/b/c` are considered to be in the same module.

!!! warning "Validated task instances only"
    This method combines *validated* task instances. For this method to work, you must have
    1. Generated 1+ Procedural Modification or LM Modify/Rewrite bugs, and 2. validated them.
    See the [Validation](harnesses.md#validation) section for more details.

**How do I run it?**
```bash
python -m swesmith.bug_gen.combine.same_file logs/bug_gen/<repo> \
  --num_patches 3 \
  --limit_per_file 15 \
  --max_combos 100
```

```bash
python -m swesmith.bug_gen.combine.same_module logs/bug_gen/<repo> \
  --num_patches 2 \
  --limit_per_module 20 \
  --max_combos 200 \
  --depth 2
```

**What artifact(s) does it produce?**

For `combine.same_file`, a `bug__combine_file__<hash>.diff` file is written to `logs/bug_gen/<repo>/<file_path>/`.

For `combine.same_module`, a `bug__combine_module__<hash>.diff` file is written to `logs/bug_gen/<repo>/combine_module/`.