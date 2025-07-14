#!/usr/bin/env python3
"""
Purpose: Export bugs from logs/run_validation to APEX task format

Usage: python -m swesmith.apex_exporter [--output-dir tasks] [--max-tasks 50]
"""

import argparse
import json
import os
import re
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from swesmith.constants import LOG_DIR_RUN_VALIDATION, TEST_OUTPUT_START, TEST_OUTPUT_END


def load_bug_report(bug_path: Path) -> Optional[Dict]:
    """Load the report.json file from a bug instance directory."""
    report_path = bug_path / "report.json"
    if not report_path.exists():
        return None
    
    try:
        with open(report_path, 'r') as f:
            return json.load(f)
    except Exception as e:
        print(f"Error loading report from {report_path}: {e}")
        return None


def extract_repo_info(bug_path: Path) -> Dict[str, str]:
    """Extract repository information from the bug path."""
    # Expected format: Instagram__MonkeyType.70c3acf6.func_pm_remove_cond__83aosj4p
    parts = bug_path.name.split('.')
    if len(parts) < 2:
        raise ValueError(f"Invalid bug path format: {bug_path.name}")
    
    # Parse repo owner and name from first part
    repo_part = parts[0]  # Instagram__MonkeyType
    owner, repo_name = repo_part.split('__', 1)
    
    # Extract commit hash
    commit_hash = parts[1]  # 70c3acf6
    
    # Extract mutation info
    mutation_id = parts[2] if len(parts) > 2 else "unknown"
    
    return {
        'owner': owner,
        'repo_name': repo_name,
        'commit_hash': commit_hash,
        'mutation_id': mutation_id,
        'full_name': f"{owner}__{repo_name}",
        'commit_short': commit_hash[:8],
        'repo_id': f"{owner}__{repo_name}.{commit_hash}"
    }


def load_setup_env_script(repo_info: Dict[str, str]) -> Optional[str]:
    """Load the setup_env.sh script for the given repository."""
    setup_env_path = Path(f"logs/build_images/env/{repo_info['repo_id']}/setup_env.sh")
    
    if not setup_env_path.exists():
        print(f"Warning: setup_env.sh not found at {setup_env_path}")
        return None
    
    try:
        with open(setup_env_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading setup_env.sh from {setup_env_path}: {e}")
        return None


def load_eval_script(bug_path: Path) -> Optional[str]:
    """Load the eval.sh script from a bug instance directory."""
    eval_path = bug_path / "eval.sh"
    if not eval_path.exists():
        print(f"Warning: eval.sh not found at {eval_path}")
        return None
    
    try:
        with open(eval_path, 'r') as f:
            return f.read()
    except Exception as e:
        print(f"Error reading eval.sh from {eval_path}: {e}")
        return None


def extract_test_commands(eval_content: str, repo_info: Dict[str, str]) -> str:
    """Extract test commands from eval.sh content between TEST_OUTPUT markers."""
    if not eval_content:
        # Fallback to basic pytest
        return f"""#!/bin/bash
cd /workdir/{repo_info['repo_name']}
pytest 
"""
    
    lines = eval_content.split('\n')
    test_commands = []
    in_test_section = False
    
    for line in lines:
        # Check for test output start marker
        if TEST_OUTPUT_START in line:
            in_test_section = True
            continue
        
        # Check for test output end marker
        if TEST_OUTPUT_END in line:
            in_test_section = False
            break
        
        # Collect test commands
        if in_test_section:
            # Skip empty lines and comments
            if line.strip() and not line.strip().startswith('#'):
                # Adapt paths and commands for Docker environment
                adapted_line = line.strip()
                
                # Replace /testbed with /workdir/{repo_name}
                adapted_line = adapted_line.replace('/testbed', f'/workdir/{repo_info["repo_name"]}')
                
                # Remove conda activation since it's handled in Docker
                if 'source /opt/miniconda3/bin/activate' in adapted_line:
                    # Extract just the command part after conda activation
                    if ';' in adapted_line:
                        parts = adapted_line.split(';')
                        # Find the actual test command (usually the last part)
                        for part in parts:
                            part = part.strip()
                            if part and not part.startswith('conda activate') and not part.startswith('source'):
                                test_commands.append(part)
                    continue
                
                test_commands.append(adapted_line)
    
    if not test_commands:
        # Fallback if no test commands found
        test_commands = ['pytest']
    
    # Create the run_test.sh content
    run_test_content = f"""#!/bin/bash
cd /workdir/{repo_info['repo_name']}
{chr(10).join(test_commands)}
"""
    
    return run_test_content


def adapt_setup_env_for_docker(setup_env_content: str, repo_info: Dict[str, str]) -> str:
    """Adapt the setup_env.sh content for Docker environment."""
    if not setup_env_content:
        # Fallback to basic setup if no setup_env.sh found
        return f"""#!/bin/bash
# Initialize conda for the current shell session
eval "$(conda shell.bash hook)"
conda create -n testbed python=3.10 -yq
conda activate testbed
pip install -e .
pip install pytest

# Set up bash to automatically activate testbed environment
echo "source /opt/miniconda3/etc/profile.d/conda.sh" >> /root/.bashrc
echo "conda activate testbed" >> /root/.bashrc
"""
    
    lines = setup_env_content.split('\n')
    adapted_lines = []
    
    # Skip the git clone line since repository is already cloned in Docker
    skip_git_clone = False
    in_yaml_section = False
    yaml_end_marker = None
    
    for line in lines:
        # Skip git clone commands
        if line.strip().startswith('git clone'):
            skip_git_clone = True
            continue
        
        # Skip cd /testbed since we'll be in the right directory
        if line.strip().startswith('cd /testbed'):
            # Replace with cd to the actual repo directory in Docker
            adapted_lines.append(f"cd /workdir/{repo_info['repo_name']}")
            continue
        
        # Detect YAML section start
        if "cat <<'EOF_" in line and "swesmith_environment.yml" in line:
            in_yaml_section = True
            yaml_end_marker = line.split("'")[1]  # Extract the EOF marker
            adapted_lines.append(line)
            continue
        
        # Detect YAML section end
        if in_yaml_section and line.strip() == yaml_end_marker:
            in_yaml_section = False
            adapted_lines.append(line)
            continue
        
        # Modify prefix in YAML section to use Docker conda path
        if in_yaml_section and line.strip().startswith('prefix:'):
            adapted_lines.append("prefix: /opt/miniconda3/envs/testbed")
            continue
        
        # Add conda initialization at the beginning if not present
        if line.strip().startswith('source /opt/miniconda3/bin/activate'):
            adapted_lines.append('# Initialize conda for the current shell session')
            adapted_lines.append('eval "$(conda shell.bash hook)"')
            continue
        
        # Keep other lines as they are
        adapted_lines.append(line)
    
    # Add bash setup at the end
    adapted_lines.extend([
        '',
        '# Set up bash to automatically activate testbed environment',
        'echo "source /opt/miniconda3/etc/profile.d/conda.sh" >> /root/.bashrc',
        'echo "conda activate testbed" >> /root/.bashrc'
    ])
    
    return '\n'.join(adapted_lines)


def create_build_sh(repo_info: Dict[str, str]) -> str:
    """Create the build.sh content dynamically from setup_env.sh."""
    setup_env_content = load_setup_env_script(repo_info)
    return adapt_setup_env_for_docker(setup_env_content, repo_info)


def create_task_yaml(repo_info: Dict[str, str], task_id: str) -> str:
    """Create the task.yaml content."""
    return f"""id: {task_id}
prompt: |
  You are given a source code repository in /workdir/{{{repo_info['repo_name']}}}.

  The repository have some failing tests. Can you fix the bugs and make all tests pass?

  Note:
  - you can use `run_test.sh` to run the tests.
  - IMPORTANT: YOU SHOULD NOT MODIFY THE TEST FILES including `run_test.sh`.
  - You are only allowed to modify the source code in the repository.
  - Repository dependencies are installed in the conda `testbed` environment.



metadata:
  difficulty: medium
  category: bug_fix
  required_tools:
    - bash
    - str_replace_editor
  tags:
    - bug_fix
    - python
    - {repo_info['repo_name'].lower()}
  time_limit: 1800
  required_resources: 2vcpu+8gib 
"""


def create_grader_py(repo_info: Dict[str, str]) -> str:
    """Create the grader.py content."""
    return f"""import subprocess

from apex_arena._types import GradingResult


def grade(transcript: str) -> GradingResult:
    \"\"\"Grade the {repo_info['repo_name']} task by running pytest.\"\"\"

    subscores = {{"pytest": 0.0}}

    feedback_parts = []

    try:
        result = subprocess.run(
            ["bash", "-c", "source /opt/miniconda3/etc/profile.d/conda.sh && conda activate testbed && /workdir/run_test.sh"],
            capture_output=True,
            text=True,
            timeout=300,
        )

        if result.returncode == 0:
            subscores["pytest"] = 1.0
            feedback_parts.append("✓ pytest passed")
        else:
            subscores["pytest"] = 0.0
            feedback_parts.append(f"✗ pytest failed: {{result.stderr}} || {{result.stdout}}")

    except subprocess.TimeoutExpired:
        feedback_parts.append("✗ pytest timed out")
    except Exception as e:
        feedback_parts.append(f"✗ Error running pytest: {{str(e)}}")

    weights = {{"pytest": 1.0}}

    total_score = sum(subscores[key] * weights[key] for key in subscores)

    return GradingResult(
        score=total_score,
        subscores=subscores,
        weights=weights,
        feedback=" | ".join(feedback_parts).replace("[", "").replace("]", ""),
    )
"""


def create_run_test_sh(repo_info: Dict[str, str], bug_path: Path) -> str:
    """Create the run_test.sh content dynamically from eval.sh."""
    eval_content = load_eval_script(bug_path)
    return extract_test_commands(eval_content, repo_info)


def create_dockerfile(repo_info: Dict[str, str]) -> str:
    """Create the Dockerfile content."""
    return f"""FROM apex_arena:base

RUN apt-get update && apt-get install -y git

# Install Miniconda
RUN wget https://repo.anaconda.com/miniconda/Miniconda3-latest-Linux-x86_64.sh -O /tmp/miniconda.sh && \\
    bash /tmp/miniconda.sh -b -p /opt/miniconda3 && \\
    rm /tmp/miniconda.sh && /opt/miniconda3/bin/conda init bash

# Add conda to PATH
ENV PATH="/opt/miniconda3/bin:$PATH"

# USER model
RUN git clone https://github.com/{repo_info['owner']}/{repo_info['repo_name']}.git /workdir/{repo_info['repo_name']}
RUN mkdir -p /workdir/patches
COPY patch.diff /workdir/patches
RUN cd /workdir/{repo_info['repo_name']} && git checkout {repo_info['commit_hash']}
RUN cd /workdir/{repo_info['repo_name']} && git apply /workdir/patches/patch.diff
RUN rm -rf /workdir/patches
# Remove git history so the model can't see the patch being applied
RUN rm -rf /workdir/{repo_info['repo_name']}/.git

# USER root
RUN mkdir -p /test
COPY build.sh /test/build.sh
COPY run_test.sh /workdir/run_test.sh
RUN chmod +x /test/build.sh
RUN chmod +x /workdir/run_test.sh
RUN cd /workdir/{repo_info['repo_name']} && /test/build.sh 
"""


def create_apex_task(bug_path: Path, output_dir: Path) -> bool:
    """Create an APEX task from a bug instance."""
    try:
        # Extract repository information
        repo_info = extract_repo_info(bug_path)
        
        # Create task ID
        task_id = f"{repo_info['owner']}-{repo_info['repo_name']}-{repo_info['commit_short']}-{repo_info['mutation_id']}"
        
        # Create task directory
        task_dir = output_dir / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Create task.yaml
        with open(task_dir / "task.yaml", 'w') as f:
            f.write(create_task_yaml(repo_info, task_id))
        
        # Create grader.py
        with open(task_dir / "grader.py", 'w') as f:
            f.write(create_grader_py(repo_info))
        
        # Create run_test.sh (now dynamic from eval.sh)
        with open(task_dir / "run_test.sh", 'w') as f:
            f.write(create_run_test_sh(repo_info, bug_path))
        os.chmod(task_dir / "run_test.sh", 0o755)
        
        # Create build.sh (now dynamic)
        with open(task_dir / "build.sh", 'w') as f:
            f.write(create_build_sh(repo_info))
        os.chmod(task_dir / "build.sh", 0o755)
        
        # Create Dockerfile
        with open(task_dir / "Dockerfile", 'w') as f:
            f.write(create_dockerfile(repo_info))
        
        # Copy patch.diff
        patch_src = bug_path / "patch.diff"
        patch_dst = task_dir / "patch.diff"
        if patch_src.exists():
            shutil.copy2(patch_src, patch_dst)
        else:
            print(f"Warning: No patch.diff found in {bug_path}")
            return False
        
        return True
        
    except Exception as e:
        print(f"Error creating APEX task from {bug_path}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Export bugs from logs/run_validation to APEX task format"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path("tasks"),
        help="Output directory for APEX tasks (default: tasks)"
    )
    parser.add_argument(
        "--max-tasks",
        type=int,
        default=50,
        help="Maximum number of tasks to export (default: 50)"
    )
    parser.add_argument(
        "--filter-repo",
        type=str,
        help="Filter to specific repository (e.g., 'Instagram__MonkeyType')"
    )
    
    args = parser.parse_args()
    
    # Ensure output directory exists
    args.output_dir.mkdir(parents=True, exist_ok=True)
    
    # Find all validation runs
    validation_dir = Path(LOG_DIR_RUN_VALIDATION)
    if not validation_dir.exists():
        print(f"Validation directory not found: {validation_dir}")
        return
    
    exported_count = 0
    skipped_count = 0
    
    # Iterate through all repo directories
    for repo_dir in validation_dir.iterdir():
        if not repo_dir.is_dir():
            continue
        
        # Apply repository filter if specified
        if args.filter_repo and not repo_dir.name.startswith(args.filter_repo):
            continue
        
        print(f"Processing repository: {repo_dir.name}")
        
        # Iterate through all bug instances
        for bug_path in repo_dir.iterdir():
            if not bug_path.is_dir():
                continue
            
            # Skip if we've reached the max tasks
            if exported_count >= args.max_tasks:
                print(f"Reached maximum tasks limit: {args.max_tasks}")
                break
            
            # Load bug report
            report = load_bug_report(bug_path)
            if report is None:
                skipped_count += 1
                continue
            
            # Check if bug has FAIL_TO_PASS entries
            fail_to_pass = report.get("FAIL_TO_PASS", [])
            if not fail_to_pass:
                print(f"  Skipping {bug_path.name}: No FAIL_TO_PASS entries")
                skipped_count += 1
                continue
            
            print(f"  Converting {bug_path.name} ({len(fail_to_pass)} failing tests)")
            
            # Create APEX task
            if create_apex_task(bug_path, args.output_dir):
                exported_count += 1
                print(f"    ✓ Exported successfully")
            else:
                skipped_count += 1
                print(f"    ✗ Failed to export")
        
        # Break if we've reached the max tasks
        if exported_count >= args.max_tasks:
            break
    
    print(f"\nExport complete:")
    print(f"  Exported: {exported_count} tasks")
    print(f"  Skipped: {skipped_count} tasks")
    print(f"  Output directory: {args.output_dir}")


if __name__ == "__main__":
    main() 