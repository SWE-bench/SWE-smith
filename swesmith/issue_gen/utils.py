import ast
import os
import random
from typing import Any

from pathlib import Path
from swebench.harness.constants import FAIL_TO_PASS
from swesmith.profiles import global_registry


def extract_pytest_test(
    file_path: str | Path, test_name: str, class_name: str | None = None
) -> str | None:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            tree = ast.parse(f.read())
    except Exception:
        return None

    # If class_name is provided, look inside the class
    if class_name:
        for node in tree.body:
            if isinstance(node, ast.ClassDef) and node.name == class_name:
                for method in node.body:
                    if isinstance(method, ast.FunctionDef) and method.name == test_name:
                        return ast.unparse(method)  # Extract function from class
    else:
        # Look for a top-level function
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name == test_name:
                return ast.unparse(node)  # Extract function

    return None


def get_test_function(instance: dict, idx: int | None = None) -> dict[str, Any]:
    # test names are in pytest format (e.g., test_file::test_name)
    test = (
        random.choice(instance[FAIL_TO_PASS])
        if idx is None
        else instance[FAIL_TO_PASS][idx]
        if idx < len(instance[FAIL_TO_PASS])
        else instance[FAIL_TO_PASS][-1]
    )
    class_name = None
    if "::" not in test:
        test_file = "test.py"
        test_name = test.split()[0]
    else:
        test_file, test_name = test.split("::", 1)
        if "::" in test_name:
            class_name, test_name = test_name.split("::", 1)
        # Remove any parameters from the test name
        test_name = test_name.split("[")[0]

    # Clone repo for instance
    repo = instance["repo"]
    repo_name = repo.split("/")[-1]
    cloned = global_registry.get(repo_name).clone()

    # Update test_file to be relative to the repo
    test_file = os.path.join(repo_name, test_file)

    return {
        "test_src": extract_pytest_test(test_file, test_name, class_name),
        "test_file": test_file,
        "test_name": test_name,
        "class_name": class_name,
        "repo_name": repo_name,
        "cloned": cloned,
    }
