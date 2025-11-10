import hashlib
import os
import subprocess

from dotenv import load_dotenv
from itertools import combinations
from swesmith.constants import TEMP_PATCH, BugRewrite, CodeEntity

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


def get_bug_directory(log_dir, candidate: CodeEntity):
    """Get the bug directory path for a given candidate."""
    signature_hash = hashlib.sha256(candidate.signature.encode()).hexdigest()[:8]
    return (
        log_dir
        / candidate.file_path.replace("/", "__")
        / f"{candidate.name}_{signature_hash}"
    )


def get_combos(items, r, max_combos) -> list[tuple]:
    """Get `max_combos` combinations of items of length r or greater."""
    all_combos = []
    for new_combo in combinations(items, r):
        all_combos.append(new_combo)
        if max_combos != -1 and len(all_combos) >= max_combos:
            break
    return sorted(all_combos, key=len)


def get_patch(repo: str, reset_changes: bool = False, file_path: str | None = None):
    """Get the patch for the current changes in a Git repository.
    
    Args:
        repo: Path to the git repository
        reset_changes: Whether to reset changes after generating patch
        file_path: If provided, only add this specific file (prevents staging unrelated files)
    """
    if (
        not os.path.isdir(repo)
        or subprocess.run(["git", "-C", repo, "status"], **DEVNULL).returncode != 0
    ):
        raise FileNotFoundError(f"'{repo}' is not a valid Git repository.")

    # Only add the specific file if provided, otherwise add all changes
    if file_path:
        subprocess.run(["git", "-C", repo, "add", file_path], check=True, **DEVNULL)
    else:
        subprocess.run(["git", "-C", repo, "add", "-A"], check=True, **DEVNULL)
    
    patch = subprocess.run(
        ["git", "-C", repo, "diff", "--staged", "--binary"],
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
        # Try to reset, if it fails, try to recover by rebuilding the index
        try:
            subprocess.run(["git", "-C", repo, "reset", "--hard"], check=True, **DEVNULL)
        except subprocess.CalledProcessError:
            # Git index might be corrupted, try to fix it
            subprocess.run(["git", "-C", repo, "read-tree", "HEAD"], **DEVNULL)
            subprocess.run(["git", "-C", repo, "reset", "--hard"], **DEVNULL)
        subprocess.run(["git", "-C", repo, "clean", "-fdx"], check=True, **DEVNULL)
    return patch
