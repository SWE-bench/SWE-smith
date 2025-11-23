# Shadowing Bug Injection (Design Overview)

Shadowing bugs are a class of subtle semantic errors introduced by creating new locally scoped names that unintentionally override or obscure names defined in outer scopes, imported modules, or global configuration structures. Unlike simple syntactic or type errors, shadowing mistakes preserve Python’s validity—code continues to run, often producing superficially plausible outputs—while silently violating assumptions that other parts of the system rely on. This makes shadowing perfect for SWE-agent training: the perturbation is “close to the original,” easy to evaluate via tests, and requires meaningful reasoning to repair.

Traditional linters and static analyzers only catch a narrow subset of trivial shadowing cases (e.g., overriding a builtin). The technique defined here focuses exclusively on linter-evasive forms: shadowing inside closures, branch-local rebinding, dynamic import masking, alias collisions, and name reuse that subtly changes the type, behavior, or lifetime of a value. These bugs do not introduce any syntax errors or structural damage. Instead, they disrupt semantic invariants or usage patterns—for example: overriding a global configuration object with a local literal, rebinding a helper function only on certain branches, shadowing an imported parsing library with a string, or replacing an accumulator list with a scalar. Each such edit represents a minimal diff (often 2–6 tokens) but leads to behavior that diverges sharply from developer intent.

From a training perspective, shadowing bugs encourage models to internalize deeper program-analysis skills: name-resolution rules (“what symbol is actually being referenced here?”), dataflow reasoning, scoping, alias tracking, and contract inference across callsites. A capable SWE agent must observe failing tests, trace the execution path, identify the unintended overshadowed symbol, and propose a consistent fix—usually a rename or a removal of the rogue binding. This delivers a strong, focused gradient signal because the task requires conceptual understanding rather than mechanical rewriting.

Operationally, the shadowing-bug generator takes in a real function or module, identifies candidate names whose accidental reuse would be semantically harmful but syntactically allowed, and instructs an LLM to introduce exactly one such rebinding. The generated code remains valid, minimally altered, and testable; the induced failure is deterministic and localized. As a result, shadowing bugs form a high-quality category of adversarial training tasks: realistic, concise, learnable, and capable of exposing weaknesses in the model’s code-reasoning stack.

## How to Run

1.  **Environment Setup**: Ensure you are running on a Linux machine (e.g., Ubuntu) with Docker installed, as SWE-smith does not support macOS or Windows.

    If you are planning to run validation/evaluation, you must set the following environment variables to point to your own GitHub and Docker Hub accounts, effectively overriding the default `swesmith` and `jyangballin` organizations.

    ```bash
    export SWESMITH_ORG_GH="<your-github-username>"
    export SWESMITH_ORG_DH="<your-dockerhub-username>"
    ```

2.  **Generate Bugs**: Use the `shadowing.generate` module to create bugs for a specific repository.

    ```bash
    python -m swesmith.bug_gen.shadowing.generate <repo_name> \
      --config_file configs/bug_gen/shadowing.yml \
      --model <your_model> \
      --n_bugs 1
    ```

    *   `<repo_name>`: The name of the repo as recognized by SWE-smith (e.g., `tkrajina__gpxpy.09fc46b3`).
    *   `<your_model>`: The LLM model to use (e.g., `openai/gpt-4o`, `anthropic/claude-3-5-sonnet-20240620`).

    This will generate patch files and metadata in `logs/bug_gen/<repo_name>/`.
