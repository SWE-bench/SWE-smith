# Writing Config. Files for Bug Generation

To create bugs using `swesmith.bug_gen.llm.modify`, the script takes in a configuration file
that allows one to (1) define what kind of bug(s) the LLM should generate, and (2) identify
what functions to run this generation for.

Here are the steps to create a config file for creating a specific kind of bug.

1. Create a `configs/bug_gen/*.yaml file`. Typically, the naming convention is `func_<name_of_bug>.yaml`.
2. Within the `.yaml` file, define the following prompts / fields:
```yaml
name: <name of bug, usually func_*>
criteria: reference to criteria in swesmith/bug_gen/llm/criteria.py
parameters: any additional information you'd like to include + can be referenced in the prompts
system: |-
    prompt
demonstration: |-
    prompt
instance: |-
    prompt
```
3. (Optional) You can use one of the existing criteria, or create a new one in `swesmith/bug_gen/llm/criteria.py`
    * The purpose of defining a criteria is to only consider functions where it would be possible to introduce such a bug.
    * For example, if you write a prompt for off by one bugs, but the function doesn't have loops or list indexing, then it's likely the LLM cannot generate a reasonably effective and difficult bug.

> A criteria function usually follows the below form:
```python
def filter_<criteria>(code_entity: CodeEntity) -> bool:
    """
    `code_entity` is an object representing a function. It includes several
    pieces of information, most notably:
        * `src_code`: The raw string repr. of a function
        * `src_node`: An AST node representation of a function.
    """
    node = code_entity.src_node
    # Logic for checking whether a function has a property has typically been
    # enforced by checking node properties (of course, you're not limited to this)
    if satisfies_criteria:
        return True
    return False
```

Once you create the `.yaml` with a specified criteria, from this repo, run:
```bash
python -m swesmith.bug_gen.llm.modify \
    --repo datamade/usaddress \
    --model openai/gpt-4o \
    --prompt_config configs/bug_gen/func_<your config>.yml \
    --n_workers 4  # 4 parallel queries to LM etc.
```
where `--repo` should point to one of the repositories [here](https://github.com/orgs/swesmith/repositories). (Note: should just be `<owner>/<repo>`, without the `.<commit>`)
