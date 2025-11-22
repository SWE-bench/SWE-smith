"""
Purpose: Transform bug patches into SWE-bench style dataset using Modal's Image.from_registry().

This version uses Modal Sandboxes with repo-specific Docker images from Docker Hub,
avoiding Docker-in-Docker entirely.

Usage: modal run -m swesmith.harness.valid_modal_v2 --bug-patches logs/bug_gen/*_patches.json
"""

import argparse
import json
import modal
import random
import time
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from swebench.harness.constants import (
    KEY_INSTANCE_ID,
    FAIL_TO_PASS,
    LOG_REPORT,
    LOG_TEST_OUTPUT,
    DOCKER_USER,
    DOCKER_WORKDIR,
)
from swesmith.constants import (
    KEY_PATCH,
    KEY_TIMED_OUT,
    LOG_DIR_RUN_VALIDATION,
    LOG_TEST_OUTPUT_PRE_GOLD,
    REF_SUFFIX,
    TEST_OUTPUT_START,
    TEST_OUTPUT_END,
)
# Re-enabled for proper grading implementation
from swesmith.harness.grading import get_valid_report as local_get_valid_report
from swesmith.profiles import registry as local_registry

# Modal app setup
app = modal.App("swesmith-validation-v2")


@dataclass
class ValidationOutput:
    """Output from a single validation run."""
    instance_id: str
    docker_image: str
    status: str  # 'timeout', 'fail', '0_f2p', '1+_f2p'
    report: dict
    test_output: str
    run_log: str
    errored: bool


# Coordinator image needs swesmith for proper grading (registry + log parsers)
# Test commands are in instance data (SWE-bench style) but we still need
# the registry for log parsing in get_valid_report
coordinator_image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("git")
    .pip_install(
        "swebench",
        "unidiff",
        "tree-sitter",
        "tree-sitter-languages",
    )
    .run_commands(
        "git clone https://github.com/AlienKevin/SWE-smith.git /swesmith",
        "cd /swesmith && pip install -e .",
    )
)


# Cache for Modal images by Docker image name
_image_cache = {}

def get_modal_image(docker_image_name: str) -> modal.Image:
    """Get or create Modal image from Docker registry (cached)."""
    if docker_image_name not in _image_cache:
        _image_cache[docker_image_name] = modal.Image.from_registry(
            docker_image_name,
            add_python="3.11"
        )
    return _image_cache[docker_image_name]


@app.function(
    image=coordinator_image,
    timeout=5 * 60,  # 5 minute per instance
    cpu=1,
)
def run_validation_single(
    instance_json: str,
    docker_image_name: str,
) -> ValidationOutput:
    """
    Run validation for a single instance using Modal Sandbox.
    
    This function runs in parallel via Modal's .map() - one invocation per instance.
    
    Args:
        instance_json: JSON string of a single instance
        docker_image_name: Docker image name (e.g., jyangballin/swesmith.x86_64.repo.commit)
        
    Returns:
        ValidationOutput object
    """
    instance = json.loads(instance_json)
    instance_id = instance[KEY_INSTANCE_ID]
    print(f"Running validation for {instance_id}...")
    
    # Get Modal image for this Docker image
    repo_image = get_modal_image(docker_image_name)
    
    sandbox = None
    try:
        # Add random jitter to respect 5/s rate limit
        # With 264 tasks, this spreads them over ~53 seconds minimum
        jitter = random.uniform(0.2, 1.0)  # Random delay 200-1000ms
        time.sleep(jitter)
        
        # Create a sandbox with retry logic for rate limiting
        max_retries = 5
        for attempt in range(max_retries):
            try:
                sandbox = modal.Sandbox.create(
                    image=repo_image,
                    timeout=60 * 10,  # 10 minutes per instance
                    cpu=2,
                )
                break  # Success!
            except Exception as e:
                if "rate limit" in str(e).lower() and attempt < max_retries - 1:
                    # Exponential backoff: 1s, 2s, 4s, 8s
                    backoff = 2 ** attempt
                    print(f"Rate limited for {instance_id}, retrying in {backoff}s...")
                    time.sleep(backoff)
                else:
                    raise  # Re-raise if not rate limit or final attempt
        
        # Run validation commands in the sandbox
        # Note: The Docker image already has the repo at the correct commit,
        # so we don't need to checkout anything. Just apply patch and test.
        
        # Get test command from profile registry
        from swesmith.profiles import registry as test_registry
        rp = test_registry.get_from_inst(instance)
        test_command = rp.test_cmd
        
        # Create eval script (mirrors utils.py lines 211-223)
        eval_script = "\n".join([
            "#!/bin/bash",
            "set -uxo pipefail",
            f"cd {DOCKER_WORKDIR}",
            f": '{TEST_OUTPUT_START}'",
            test_command,
            f": '{TEST_OUTPUT_END}'",
        ]) + "\n"
        
        # Write eval script to container
        write_eval_result = sandbox.exec(
            "sh", "-c", f"cat > /eval.sh << 'EOF'\n{eval_script}\nEOF",
        )
        write_eval_result.wait()
        
        # Make it executable
        chmod_result = sandbox.exec("chmod", "+x", "/eval.sh")
        chmod_result.wait()
        
        # 1. Run tests WITHOUT patch (pre-gold/reference) to get baseline
        # Redirect stderr to stdout (2>&1) to preserve output order for marker parsing
        test_result_pregold = sandbox.exec(
            "sh", "-c", "/bin/bash /eval.sh 2>&1",
            workdir=DOCKER_WORKDIR,
        )
        test_result_pregold.wait()
        
        # Extract pre-gold test output (stdout now contains both streams in order)
        test_output_pregold = test_result_pregold.stdout.read() if test_result_pregold.stdout else ""
        
        # 2. Apply patch if provided (mirroring run_patch_in_container logic)
        if KEY_PATCH in instance and instance[KEY_PATCH]:
            patch_content = instance[KEY_PATCH]
            
            # Write patch to file in container
            write_result = sandbox.exec(
                "sh", "-c", f"cat > /tmp/patch.diff << 'EOF'\n{patch_content}\nEOF",
            )
            write_result.wait()
            
            # Apply patch using git apply
            patch_result = sandbox.exec(
                "git", "apply", "/tmp/patch.diff",
                workdir=DOCKER_WORKDIR,
            )
            patch_result.wait()
            
            if patch_result.returncode != 0:
                error_log = patch_result.stderr.read() if patch_result.stderr else ""
                return ValidationOutput(
                    instance_id=instance_id,
                    docker_image=docker_image_name,
                    status="fail",
                    report={"error": "Failed to apply patch"},
                    test_output="",
                    run_log=error_log,
                    errored=True,
                )
        
        # 3. Run tests WITH patch (post-gold) to see what the bug breaks
        # Redirect stderr to stdout (2>&1) to preserve output order for marker parsing
        test_result_postgold = sandbox.exec(
            "sh", "-c", "/bin/bash /eval.sh 2>&1",
            workdir=DOCKER_WORKDIR,
        )
        test_result_postgold.wait()
        
        # Extract post-gold test output (stdout now contains both streams in order)
        test_output_postgold = test_result_postgold.stdout.read() if test_result_postgold.stdout else ""
        
        # 4. Grade using get_valid_report (mirrors valid.py lines 130-136)
        # Compare pre-gold (without patch) vs post-gold (with patch) outputs
        try:
            from swesmith.harness.grading import get_valid_report as grading_get_valid_report
            from swesmith.profiles import registry as grading_registry
            
            # Write outputs to temp files for grading
            import tempfile
            with tempfile.NamedTemporaryFile(mode='w', suffix='_pregold.txt', delete=False) as f:
                f.write(test_output_pregold)
                pregold_path = f.name
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='_postgold.txt', delete=False) as f:
                f.write(test_output_postgold)
                postgold_path = f.name
            
            try:
                # Get repo profile for log parsing
                rp = grading_registry.get_from_inst(instance)
                
                # Use get_valid_report to compare pre vs post
                # NOTE: Counter-intuitive semantics - pregold=WITH patch, postgold=WITHOUT patch
                report = grading_get_valid_report(
                    val_pregold_path=postgold_path,  # WITH patch (buggy - should fail tests)
                    val_postgold_path=pregold_path,   # WITHOUT patch (clean - should pass tests)
                    instance=instance,
                )
                
                # Determine status based on FAIL_TO_PASS count
                if len(report.get(FAIL_TO_PASS, [])) == 0:
                    status = "0_f2p"
                else:
                    status = "1+_f2p"
            finally:
                # Clean up temp files
                import os
                try:
                    os.unlink(pregold_path)
                    os.unlink(postgold_path)
                except:
                    pass
            
        except Exception as e:
            print(f"Error during grading for {instance_id}: {e}")
            report = {"error": str(e)}
            status = "fail"
        
        return ValidationOutput(
            instance_id=instance_id,
            docker_image=docker_image_name,
            status=status,
            report=report,
            test_output=test_output_postgold,  # Post-gold output (with patch)
            run_log=test_output_pregold,  # Pre-gold output with bash markers (stdout+stderr merged)
            errored=False,
        )
            
    except Exception as e:
        print(f"Error validating {instance_id}: {e}")
        return ValidationOutput(
            instance_id=instance_id,
            docker_image=docker_image_name,
            status="fail",
            report={"error": str(e)},
            test_output="",
            run_log=str(e),
            errored=True,
        )
    finally:
        # Clean up sandbox
        if sandbox is not None:
            try:
                sandbox.terminate()
            except Exception:
                pass  # Ignore cleanup errors


@app.local_entrypoint()
def main(
    bug_patches: str,
    redo_existing: bool = False,
    max_workers: int = 10,
) -> None:
    """
    Main entry point for Modal-based validation using Image.from_registry().
    
    Args:
        bug_patches: Path to JSON file with bug patches
        redo_existing: Whether to redo existing validations
        max_workers: Maximum number of parallel batches (one per unique Docker image)
    """
    print(f"Running Modal validation (v2) for {bug_patches}...")
    print(f"Using Image.from_registry() to load repo-specific Docker images")
    
    # Load patches
    with open(bug_patches, "r") as f:
        bug_patches_data = json.load(f)
    
    bug_patches_data = [
        {
            **x,
            KEY_PATCH: x.get(KEY_PATCH, x.get("model_patch")),
        }
        for x in bug_patches_data
    ]
    print(f"Found {len(bug_patches_data)} candidate patches.")
    
    # Group by Docker image (each repo has its own image)
    image_to_instances = defaultdict(list)
    for patch in bug_patches_data:
        # Extract Docker image name from repo field
        # repo field format: "Owner__RepoName.commit" (e.g., "Instagram__MonkeyType.70c3acf6")
        repo_str = patch["repo"]
        
        # Split by '.' to separate repo from commit
        if "." in repo_str:
            repo_id, commit = repo_str.rsplit(".", 1)
        else:
            repo_id = repo_str
            commit = "unknown"
        
        # repo_id format: "Owner__RepoName"
        # Convert to Docker image format: jyangballin/swesmith.x86_64.owner_1776_reponame.commit
        owner, repo_name = repo_id.split("__")
        
        docker_image = f"jyangballin/swesmith.x86_64.{owner.lower()}_1776_{repo_name.lower()}.{commit}"
        image_to_instances[docker_image].append(patch)
    
    print(f"\nGrouped into {len(image_to_instances)} unique Docker images:")
    for image, instances in image_to_instances.items():
        print(f"  - {image}: {len(instances)} instances")
    
    start_time = time.time()
    
    # Prepare all tasks for parallel execution
    print("\nStarting Modal validation...")
    print(f"Submitting {len(bug_patches_data)} instances for parallel execution...")
    
    # Create list of (instance_json, docker_image) tuples for all instances
    tasks = []
    for docker_image, instances in image_to_instances.items():
        for instance in instances:
            tasks.append((json.dumps(instance), docker_image))
    
    print(f"Total tasks to run in parallel: {len(tasks)}")
    
    # Run all validations in parallel using Modal's .starmap()
    with modal.enable_output():
        all_results = list(run_validation_single.starmap(
            tasks,
            return_exceptions=True,
        ))
    
    # Process results
    stats = {"fail": 0, "timeout": 0, "0_f2p": 0, "1+_f2p": 0, "error": 0}
    
    for result in all_results:
        # Handle exceptions from starmap
        if isinstance(result, Exception):
            print(f"Task failed with exception: {result}")
            stats["error"] += 1
            continue
        
        # Skip if not a ValidationOutput
        if not isinstance(result, ValidationOutput):
            print(f"Unexpected result type: {type(result)}")
            stats["error"] += 1
            continue
        
        if result.errored:
            stats["error"] += 1
        else:
            stats[result.status] += 1
        
        # Save logs locally
        # Extract repo from instance_id (format: Owner__RepoName.commit.strategy__hash)
        # We want to save to: LOG_DIR_RUN_VALIDATION / "Owner__RepoName.commit" / instance_id
        instance_id_parts = result.instance_id.split(".")
        if len(instance_id_parts) >= 2:
            repo_dir = f"{instance_id_parts[0]}.{instance_id_parts[1]}"  # Owner__RepoName.commit
        else:
            repo_dir = result.instance_id.split(".", 1)[0]
        
        log_dir = LOG_DIR_RUN_VALIDATION / repo_dir / result.instance_id
        log_dir.mkdir(parents=True, exist_ok=True)
        
        with open(log_dir / "run_instance.log", "w") as f:
            f.write(result.run_log)
        with open(log_dir / LOG_TEST_OUTPUT, "w") as f:
            f.write(result.test_output)
        with open(log_dir / LOG_REPORT, "w") as f:
            json.dump(result.report, f, indent=4)
    
    elapsed = time.time() - start_time
    
    print("\n" + "=" * 60)
    print("Modal Validation Complete!")
    print("=" * 60)
    print(f"Total time: {elapsed:.1f} seconds ({elapsed/60:.1f} minutes)")
    print(f"Average time per instance: {elapsed/len(bug_patches_data):.1f} seconds")
    print("\nResults:")
    print(f"- Timeouts: {stats['timeout']}")
    print(f"- Failed: {stats['fail']}")
    print(f"- 0 F2P: {stats['0_f2p']}")
    print(f"- 1+ F2P: {stats['1+_f2p']}")
    print(f"- Errors: {stats['error']}")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Transform bug patches into SWE-bench dataset using Modal (v2)."
    )
    parser.add_argument(
        "--bug-patches",
        type=str,
        required=True,
        help="Json file containing bug patches.",
    )
    parser.add_argument(
        "--redo-existing",
        action="store_true",
        help="Redo completed validation instances.",
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=10,
        help="Maximum number of parallel batches (default: 10)",
    )
    args = parser.parse_args()
    
    main(
        bug_patches=args.bug_patches,
        redo_existing=args.redo_existing,
        max_workers=args.max_workers,
    )
