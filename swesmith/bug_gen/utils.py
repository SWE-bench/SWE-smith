import os
import subprocess

from dotenv import load_dotenv
from itertools import combinations
from pathlib import Path
from swesmith.bug_gen.adapters import get_entities_from_file
from swesmith.constants import TEMP_PATCH
from swesmith.utils import BugRewrite, CodeEntity

load_dotenv()


DEVNULL = {"stdout": subprocess.DEVNULL, "stderr": subprocess.DEVNULL}


def apply_code_change(candidate: CodeEntity, bug: BugRewrite) -> None:
    """Replaces lines in a file between start_line and end_line (inclusive) with replacement_code."""
    with open(candidate.file_path, "r") as file:
        lines = file.readlines()
    if (
        candidate.line_start < 1
        or candidate.line_end > len(lines)
        or candidate.line_start > candidate.line_end
    ):
        raise ValueError("Invalid line range specified.")
    change = [
        f"{' ' * candidate.indent_level * candidate.indent_size}{x}"
        if len(x.strip()) > 0
        else x
        for x in bug.rewrite.splitlines(keepends=True)
    ]

    # If the last line being replaced ends with one or more newlines,
    # ensure the last line of the replacement also end with the same number of newlines.
    curr_last_line = lines[candidate.line_end - 1]
    num_newlines = len(curr_last_line) - len(curr_last_line.rstrip("\n"))
    change[-1] = change[-1].rstrip("\n") + "\n" * num_newlines

    with open(candidate.file_path, "w") as file:
        # NOTE: This assumes that the candidate.line_start and candidate.line_end
        # are 1-based indices, as is common in many text editors.
        file.writelines(
            (lines[: candidate.line_start - 1] + change + lines[candidate.line_end :])
        )


def apply_patches(repo: str, patch_files: list[str]) -> str | None:
    """Apply multiple patches to a target local directory, and get the combined patch."""
    cwd = os.getcwd()
    os.chdir(repo)
    try:
        for patch_file in patch_files:
            subprocess.run(
                ["git", "apply", os.path.join("..", patch_file)], check=True, **DEVNULL
            )
        patch = get_patch(os.getcwd(), reset_changes=True)

        # Sanity check that merged patch applies cleanly
        with open(TEMP_PATCH, "w") as f:
            f.write(patch)
        subprocess.run(["git", "apply", TEMP_PATCH], check=True, **DEVNULL)
        return patch
    except subprocess.CalledProcessError:
        return None
    finally:
        if os.path.exists(TEMP_PATCH):
            os.remove(TEMP_PATCH)
        subprocess.run(["git", "-C", ".", "reset", "--hard"], check=True, **DEVNULL)
        subprocess.run(["git", "clean", "-fdx"], check=True, **DEVNULL)
        os.chdir(cwd)


def extract_entities_from_directory(
    directory_path: str,
    exclude_tests: bool = True,
    max_entities: int = -1,
) -> list[CodeEntity]:
    """
    Extracts entities (functions, classes, etc.) from Python files in a directory.
    Args:
        directory_path (str): Path to the directory to scan.
        exclude_tests (bool): Whether to exclude test files and directories.
    Returns:
        List[CodeEntity]: List of CodeEntity objects containing entity information.
    """
    entities = []
    for root, _, files in os.walk(directory_path):
        if exclude_tests and any([x in root for x in ["/tests", "/test", "/testing"]]):
            continue
        for file in files:
            if exclude_tests and (
                file.startswith("test_") or file.rsplit(".", 1)[0].endswith("_test")
            ):
                continue

            file_path = os.path.join(root, file)

            try:
                open(file_path, "r", encoding="utf-8").close()
            except:
                continue

            file_ext = Path(file_path).suffix[1:]
            if file_ext not in get_entities_from_file:
                continue
            get_entities_from_file[file_ext](entities, file_path, max_entities)

    return entities


def get_combos(items, r, max_combos) -> list[tuple]:
    """Get `max_combos` combinations of items of length r or greater."""
    all_combos = []
    for new_combo in combinations(items, r):
        all_combos.append(new_combo)
        if max_combos != -1 and len(all_combos) >= max_combos:
            break
    return sorted(all_combos, key=len)


def get_patch(repo: str, reset_changes: bool = False):
    """Get the patch for the current changes in a Git repository."""
    if (
        not os.path.isdir(repo)
        or subprocess.run(["git", "-C", repo, "status"], **DEVNULL).returncode != 0
    ):
        raise FileNotFoundError(f"'{repo}' is not a valid Git repository.")

    subprocess.run(["git", "-C", repo, "add", "-A"], check=True, **DEVNULL)
    patch = subprocess.run(
        ["git", "-C", repo, "diff", "--staged"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    if len(patch.strip()) == 0:
        return None
    for cleanup_cmd in [
        f"git -C {repo} restore --staged .",
        f"git -C {repo} reset --hard",
        f"git -C {repo} clean -fdx",
    ]:
        subprocess.run(cleanup_cmd.split(), check=True, **DEVNULL)
    patch_file = os.path.join(repo, TEMP_PATCH)
    with open(patch_file, "w") as f:
        f.write(patch)
    subprocess.run(["git", "-C", repo, "apply", TEMP_PATCH], check=True)
    if reset_changes:
        subprocess.run(["git", "-C", repo, "reset", "--hard"], check=True, **DEVNULL)
        subprocess.run(["git", "-C", repo, "clean", "-fdx"], check=True, **DEVNULL)
    return patch
