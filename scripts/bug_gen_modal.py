"""
Modal Bug Generation & Validation Script
All logs are persisted to a Modal Volume.

Run with: modal run scripts/bug_gen.py [OPTIONS]
"""

import asyncio
import json
import logging
import shutil
import sys
from pathlib import Path

import modal

modal.enable_output()


# ============================================================================
# Asyncio Exception Logging (to diagnose 'socket.send() raised exception')
# ============================================================================


class DeduplicatingFilter(logging.Filter):
    """A logging filter that suppresses repeated log messages after a threshold."""

    def __init__(self, max_repeats: int = 5):
        super().__init__()
        self.max_repeats = max_repeats
        self._message_counts: dict[str, int] = {}

    def filter(self, record: logging.LogRecord) -> bool:
        # Create a key from the log message (truncate to avoid memory issues)
        msg_key = f"{record.levelname}:{record.getMessage()[:100]}"

        self._message_counts[msg_key] = self._message_counts.get(msg_key, 0) + 1
        count = self._message_counts[msg_key]

        if count <= self.max_repeats:
            if count == self.max_repeats:
                # Modify the message to indicate suppression
                record.msg = f"{record.msg} (further repeats will be suppressed)"
            return True
        elif count % 1000 == 0:
            # Log summary every 1000 occurrences
            record.msg = f"[Repeated {count}x] {record.msg}"
            return True
        return False


def setup_asyncio_exception_logging():
    """
    Configure asyncio to limit duplicate log messages and capture exception details.

    The 'socket.send() raised exception' warning is logged by asyncio's
    _SelectorSocketTransport.write() when an SSL/socket error occurs. This
    adds a deduplication filter to prevent log spam.
    """
    # Get the asyncio logger and clear any existing handlers to avoid duplicates
    asyncio_logger = logging.getLogger("asyncio")

    # Remove existing handlers to prevent duplicate output
    asyncio_logger.handlers.clear()

    # Add a deduplicating filter
    dedup_filter = DeduplicatingFilter(max_repeats=5)

    # Set up a detailed formatter with the dedup filter
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s - [%(filename)s:%(lineno)d]"
        )
    )
    handler.addFilter(dedup_filter)
    asyncio_logger.addHandler(handler)
    asyncio_logger.setLevel(logging.WARNING)  # Only warnings and above
    asyncio_logger.propagate = (
        False  # Don't propagate to root logger (prevents duplicates)
    )

    # Store exception counts to avoid log spam for unhandled exceptions
    _exception_counts: dict[str, int] = {}

    def custom_exception_handler(loop, context):
        """Custom exception handler that logs full exception details with deduplication."""
        exception = context.get("exception")
        message = context.get("message", "Unknown async error")

        # Create a key for rate limiting
        exc_type = type(exception).__name__ if exception else "Unknown"
        exc_key = f"{exc_type}:{message[:50]}"

        _exception_counts[exc_key] = _exception_counts.get(exc_key, 0) + 1
        count = _exception_counts[exc_key]

        # Only log full details for first 5 occurrences of each type
        if count <= 5:
            if exception:
                logging.error(
                    f"Asyncio exception #{count}: {message}\n"
                    f"  Exception type: {type(exception).__name__}\n"
                    f"  Exception: {exception}\n"
                    f"  Context: {context}"
                )
                if count == 5:
                    logging.warning(
                        f"  (Further '{exc_key}' exceptions will be suppressed)"
                    )
            else:
                logging.error(f"Asyncio error #{count}: {message} | Context: {context}")
        elif count % 1000 == 0:
            # Log summary every 1000 occurrences
            logging.warning(f"Asyncio '{exc_key}' exception count: {count}")

    return custom_exception_handler


# ============================================================================
# Constants & Configuration
# ============================================================================

APP_NAME = "swesmith-bug-gen"
VOLUME_NAME = "swesmith-bug-gen"
MINUTES = 60
MODAL_TIMEOUT = 10 * MINUTES
SANDBOX_RATE_LIMIT = 4  # Modal limits to 5/s, use 4 to be safe

LANGUAGE_TO_BASE_CLASS = {
    "python": "PythonProfile",
    "javascript": "JavaScriptProfile",
    "typescript": "TypeScriptProfile",
    "golang": "GoProfile",
    "go": "GoProfile",
    "rust": "RustProfile",
    "java": "JavaProfile",
    "c": "CProfile",
    "cpp": "CppProfile",
    "csharp": "CSharpProfile",
    "php": "PhpProfile",
}

TEST_OUTPUT_START = ">>>>> Start Test Output"
TEST_OUTPUT_END = ">>>>> End Test Output"
PREGOLD_TIMEOUT = 500  # seconds - skip post-gold if baseline exceeds this
MIN_PATCHES_FOR_VALIDATION = 50  # skip repos with fewer patches

REMOTE_VALIDATOR_SCRIPT = r"""
import sys
import json
import subprocess
import os
from pathlib import Path

# We need to make sure we can import these. 
# The image sets PYTHONPATH=/root, and swesmith is at /root/swesmith
if "/root" not in sys.path:
    sys.path.append("/root")

from swesmith.harness.grading import get_valid_report
from swesmith.constants import TEST_OUTPUT_START, TEST_OUTPUT_END

def main():
    try:
        config_path = sys.argv[1]
        with open(config_path, 'r') as f:
            config = json.load(f)
        
        test_cmd = config['test_cmd']
        output_path = Path(config['output_path'])
        baseline_path = Path(config['baseline_path'])
        baseline_text = config.get('baseline_text')
        report_path = Path(config['report_path'])
        instance = config['instance']
        
        # Ensure output directory exists (it's on a volume mount)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Run test command
        print(f"Executing test: {test_cmd}")
        
        full_cmd = f"set -uxo pipefail; : '{TEST_OUTPUT_START}'; {test_cmd} || true; : '{TEST_OUTPUT_END}'"
        
        # execution
        proc = subprocess.run(
            full_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            executable="/bin/bash"
        )
        
        output_bytes = proc.stdout
        exit_code = proc.returncode
        
        # Decode
        output_str = output_bytes.decode('utf-8', errors='replace')
        
        # Write output to volume
        output_path.write_text(output_str, encoding='utf-8')
        print(f"Saved output to {output_path}")
        
        result_summary = {
            "instance_id": instance.get("instance_id"),
            "valid": False,
            "error": None,
            "exit_code": exit_code
        }

        # Fall back to the inline pregold baseline if the mounted volume path
        # is not visible inside this sandbox yet.
        if not baseline_path.exists() and baseline_text is not None:
            baseline_path.parent.mkdir(parents=True, exist_ok=True)
            baseline_path.write_text(baseline_text, encoding='utf-8')

        # Check baseline and validate
        if baseline_path.exists():
            print(f"Baseline found at {baseline_path}, validating...")
            try:
                report = get_valid_report(
                    val_pregold_path=str(baseline_path),
                    val_postgold_path=str(output_path),
                    instance=instance
                )
                
                report_path.write_text(json.dumps(report, indent=4))
                print(f"Saved report to {report_path}")
                
                if len(report.get("PASS_TO_FAIL", [])) > 0:
                    result_summary["valid"] = True
                    print("Validation SUCCESS: Found PASS_TO_FAIL")
                else:
                    print("Validation result: No PASS_TO_FAIL")
                    
            except Exception as e:
                print(f"Validation error: {e}")
                result_summary["error"] = f"Grading error: {str(e)}"
        else:
            print(f"Baseline NOT found at {baseline_path}")
            result_summary["error"] = "Baseline not found"
            
        # Output result as JSON marked with special tags
        print(f"\n<<RESULT_JSON>>{json.dumps(result_summary)}<<RESULT_JSON>>")
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        # Fallback error result
        res = {"valid": False, "error": str(e)}
        print(f"\n<<RESULT_JSON>>{json.dumps(res)}<<RESULT_JSON>>")

if __name__ == "__main__":
    main()
"""

# ============================================================================
# Profile & Repo Utilities
# ============================================================================


def get_repos_for_language(language: str) -> list[str]:
    """Get all registered repos for a given language."""
    from swesmith.profiles import registry

    base_class_name = LANGUAGE_TO_BASE_CLASS.get(language.lower())
    if not base_class_name:
        raise ValueError(
            f"Unknown language: {language}. Supported: {list(LANGUAGE_TO_BASE_CLASS.keys())}"
        )

    return [
        f"{profile.owner}/{profile.repo}"
        for profile in registry.values()
        if profile.__class__.__name__ != base_class_name
        and base_class_name in [base.__name__ for base in profile.__class__.__mro__]
    ]


def resolve_profile(repo_name: str):
    """Resolve a profile from repo name using robust lookup."""
    from swesmith.profiles import registry

    try:
        profile = registry.get(repo_name)
        profile.arch = "x86_64"
        return profile
    except KeyError:
        for key in registry.keys():
            try:
                p = registry.get(key)
                if f"{p.owner}/{p.repo}" == repo_name:
                    p.arch = "x86_64"
                    return p
            except Exception:
                continue
    raise RuntimeError(f"No profile found for repo: {repo_name}")


# ============================================================================
# Modal Setup & Images
# ============================================================================

generator_image = (
    modal.Image.from_registry("ubuntu:22.04", add_python="3.11")
    .apt_install("git")
    .pip_install_from_pyproject("pyproject.toml", optional_dependencies=["generate"])
    .pip_install("jinja2", "litellm", "datasets", "pyyaml")
    .env({"PYTHONPATH": "/root"})
    .add_local_dir("swesmith", remote_path="/root/swesmith")
    .add_local_dir("configs", remote_path="/root/configs")
    .add_local_file(".env", remote_path="/root/.env")
)

# Global cache for validator images - populated by prebuild_validator_images()
_validator_image_cache: dict[str, modal.Image] = {}


def _create_validator_image(image_name: str) -> modal.Image:
    """Create a validator image for the given Docker image name (internal helper)."""
    return (
        modal.Image.from_registry(image_name, add_python="3.11")
        .pip_install_from_pyproject(
            "pyproject.toml", optional_dependencies=["validate"]
        )
        .env({"PYTHONPATH": "/root"})
        .add_local_dir("swesmith", remote_path="/root/swesmith")
    )


def get_validator_image(image_name: str) -> modal.Image:
    """Get or create a validator image for the given Docker image name.

    Uses the global cache if available (populated by prebuild_validator_images).
    """
    if image_name in _validator_image_cache:
        return _validator_image_cache[image_name]

    print(
        f"DEBUG: get_validator_image called for {image_name} (not cached, building...)"
    )
    image = _create_validator_image(image_name)
    _validator_image_cache[image_name] = image
    return image


async def prebuild_validator_images_async(
    repos_with_patches: dict,
) -> dict[str, modal.Image]:
    """Pre-build and cache all validator images for the given repositories.

    This builds all unique Docker images by running a simple warmup command
    in each image before any validation runs. This forces Modal to build
    and upload all images in parallel upfront.

    Returns the cache dict of image_name -> modal.Image
    """
    global _validator_image_cache

    # Collect unique image names
    unique_images = set()
    for repo, info in repos_with_patches.items():
        profile = info["profile"]
        if hasattr(profile, "image_name") and profile.image_name:
            unique_images.add(profile.image_name)

    print(f"\n{'=' * 60}")
    print(f"PRE-BUILDING VALIDATOR IMAGES ({len(unique_images)} unique images)")
    print(f"{'=' * 60}\n")

    # Filter out already-cached images
    to_build = [img for img in unique_images if img not in _validator_image_cache]

    if not to_build:
        print("All images already cached!")
        return _validator_image_cache

    print(f"Building {len(to_build)} images in parallel...")
    for i, img in enumerate(to_build, 1):
        print(f"  [{i}] {img}")

    # Create all image objects and cache them using the helper
    for img_name in to_build:
        _validator_image_cache[img_name] = _create_validator_image(img_name)

    # Now run warmup sandboxes to force Modal to build all images
    async def warmup_all():
        semaphore = asyncio.Semaphore(100)  # Limit concurrent builds

        async def warmup_image(img_name: str) -> tuple[str, bool, str]:
            """Run a simple command to force image build."""
            async with semaphore:
                try:
                    # Rate limit sandbox creation
                    await _sandbox_rate_limiter.acquire()

                    print(f"  Building: {img_name}...")
                    image = _validator_image_cache[img_name]
                    sb = await modal.Sandbox.create.aio(
                        app=app, image=image, timeout=300
                    )
                    process = await sb.exec.aio("echo", "warmup_ok", text=False)
                    output = await process.stdout.read.aio()
                    await sb.terminate.aio()
                    print(f"  ✓ Built: {img_name}")
                    return (img_name, True, "")
                except Exception as e:
                    print(f"  ✗ Failed: {img_name} - {e}")
                    return (img_name, False, str(e))

        tasks = [warmup_image(img) for img in to_build]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        return results

    print("\nWarming up images (this triggers the actual build/upload)...")
    results = await warmup_all()

    # Report results
    success = sum(1 for r in results if isinstance(r, tuple) and r[1])
    failed = len(results) - success

    print(f"\nImage build complete: {success} succeeded, {failed} failed")
    if failed > 0:
        for r in results:
            if isinstance(r, tuple) and not r[1]:
                print(f"  Failed: {r[0]} - {r[2]}")
    print()

    return _validator_image_cache


app = modal.App(APP_NAME)
# Use Volume v2 for better scalability (more files, concurrent writes, faster commits)
logs_volume = modal.Volume.from_name(VOLUME_NAME, create_if_missing=True, version=2)
LOGS_MOUNT_PATH = "/logs"  # Where the volume is mounted in Modal containers


# ============================================================================
# Volume I/O Helpers
# ============================================================================


async def volume_write_text(path: str, content: str) -> None:
    """Write text content to a path on the Modal Volume."""
    import io

    def _write():
        with logs_volume.batch_upload() as batch:
            batch.put_file(io.BytesIO(content.encode("utf-8")), path)

    await asyncio.to_thread(_write)


async def volume_write_bytes(path: str, content: bytes) -> None:
    """Write binary content to a path on the Modal Volume."""
    import io

    def _write():
        with logs_volume.batch_upload() as batch:
            batch.put_file(io.BytesIO(content), path)

    await asyncio.to_thread(_write)


async def volume_read_text(path: str) -> str | None:
    """Read text content from the Modal Volume. Returns None if file doesn't exist."""
    try:
        chunks = []
        async for chunk in logs_volume.read_file.aio(path):
            chunks.append(chunk)
        return b"".join(chunks).decode("utf-8")
    except Exception:
        return None


async def volume_file_exists(path: str) -> bool:
    """Check if a file exists on the Modal Volume."""
    try:
        # listdir is much faster than reading the file as it only fetches metadata
        await logs_volume.listdir.aio(path)
        return True
    except Exception:
        return False


async def volume_list_dir(path: str) -> list[str]:
    """List files/directories in a path on the Modal Volume."""
    try:
        entries = await logs_volume.listdir.aio(path)
        return [e.path for e in entries]
    except Exception:
        return []


# ============================================================================
# Rate Limiter for Sandbox Creation
# ============================================================================


class AsyncRateLimiter:
    """Token bucket rate limiter for controlling sandbox creation rate."""

    def __init__(self, rate: float):
        """Create rate limiter with given rate (operations per second)."""
        self.rate = rate
        self.interval = 1.0 / rate  # Time between operations
        self._lock = asyncio.Lock()
        self._last_time = 0.0

    async def acquire(self):
        """Wait until rate limit allows another operation."""
        async with self._lock:
            import time

            now = time.monotonic()
            wait_time = self._last_time + self.interval - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)
                now = time.monotonic()
            self._last_time = now


# Global rate limiter for sandbox creation (Modal limit: 5/s)
_sandbox_rate_limiter = AsyncRateLimiter(SANDBOX_RATE_LIMIT)


# ============================================================================
# Remote Bug Generation
# ============================================================================


@app.function(
    image=generator_image,
    secrets=[
        modal.Secret.from_name("GITHUB_TOKEN"),
        modal.Secret.from_name("PORTKEY_API_KEY"),
    ],
    timeout=MODAL_TIMEOUT,
    volumes={LOGS_MOUNT_PATH: logs_volume},  # Mount volume for direct writes
)
def generate_bugs_remote(
    repo_name: str,
    max_bugs: int,
    interleave: bool,
    max_entities: int,
    max_candidates: int,
    language: str,
    timeout_buffer_seconds: int = 60,
) -> dict:
    """Generate bugs for a repository on a remote Modal worker.

    Results are saved directly to the Modal Volume, reducing data transfer.
    Returns only a lightweight summary.
    """
    import sys
    from io import StringIO

    if "/root" not in sys.path:
        sys.path.append("/root")

    from swesmith.profiles import registry
    from swesmith.bug_gen.procedural.generate import main as generate_main
    from swesmith.bug_gen.collect_patches import main as collect_patches_main

    # Setup output capture
    log_buffer = StringIO()
    original_stdout, original_stderr = sys.stdout, sys.stderr

    class TeeWriter:
        def __init__(self, buffer, original):
            self.buffer, self.original = buffer, original

        def write(self, data):
            self.buffer.write(data)
            self.original.write(data)

        def flush(self):
            self.buffer.flush()
            self.original.flush()

    sys.stdout = TeeWriter(log_buffer, original_stdout)
    sys.stderr = TeeWriter(log_buffer, original_stderr)

    # Resolve repo ID
    def resolve_repo_id():
        try:
            return registry.get_from_inst(
                {"repo": repo_name, "instance_id": "dummy"}
            ).repo_name
        except Exception as e:
            print(f"Direct profile lookup failed for {repo_name}: {e}")
            target = repo_name.replace("/", "__")
            candidates = [key for key in registry.keys() if target in key]
            return candidates[0] if candidates else repo_name

    repo_id = resolve_repo_id()
    print(f"Resolved repo_id: {repo_id}")
    logs_base = Path("logs/bug_gen")

    # Volume paths for saving results
    volume_base = Path(LOGS_MOUNT_PATH)
    volume_bug_dir = volume_base / language / "bug_gen" / repo_id

    def _safe_execute(func, error_msg, *args, **kwargs):
        import traceback

        try:
            return func(*args, **kwargs)
        except Exception as e:
            print(f"{error_msg}: {e}")
            traceback.print_exc()
            return None

    def save_results_to_volume() -> dict:
        """Collect results and save directly to Modal Volume. Returns summary."""
        if not logs_base.exists():
            print(f"LOGS BASE MISSING: {logs_base}")
            return {"error": f"Logs directory {logs_base} does not exist."}

        generated_dirs = [d for d in logs_base.iterdir() if d.is_dir()]
        if not generated_dirs:
            print(f"NO DATA IN LOGS BASE. Files: {list(logs_base.glob('**/*'))}")
            return {"error": "No data generated"}

        repo_id_actual = sorted(
            generated_dirs, key=lambda x: x.stat().st_mtime, reverse=True
        )[0].name
        print(f"Detected repo_id_actual: {repo_id_actual}")

        _safe_execute(
            collect_patches_main,
            "Error in collect_patches_main",
            str(logs_base / repo_id_actual),
        )

        # Ensure volume directory exists
        volume_bug_dir.mkdir(parents=True, exist_ok=True)

        # Create and save zip
        def _save_zip():
            shutil.make_archive(
                f"/tmp/{repo_id_actual}", "zip", str(logs_base / repo_id_actual)
            )
            zip_path = f"/tmp/{repo_id_actual}.zip"
            dest_path = volume_bug_dir / "bugs.zip"
            shutil.copy(zip_path, dest_path)
            print(f"Saved bugs.zip to volume: {dest_path}")

        _safe_execute(_save_zip, "Error saving zip to volume")

        # Read and save patches
        patches_file = logs_base / f"{repo_id_actual}_all_patches.json"
        if patches_file.exists():
            patches_json = patches_file.read_text()
            patches = json.loads(patches_json)

            # Save patches to volume
            patches_dest = (
                volume_base / language / "bug_gen" / f"{repo_id}_all_patches.json"
            )
            patches_dest.write_text(patches_json)
            print(f"Saved {len(patches)} patches to volume: {patches_dest}")

            if not patches:
                # Mark as done with 0 bugs
                (volume_bug_dir / "done.txt").write_text(
                    "Generation completed: 0 bugs generated"
                )
                return {"total_bugs": 0, "patches": []}

            # Mark as done
            (volume_bug_dir / "done.txt").write_text(
                f"Generation completed: {len(patches)} bugs generated"
            )
            logs_volume.commit()  # Force internal commit to persist done.txt immediately
            return {"total_bugs": len(patches), "patches": patches}
        else:
            print(
                f"Patches file not found. Available: {[p.name for p in logs_base.iterdir()]}"
            )
            (volume_bug_dir / "error.txt").write_text("No patches_json generated")
            logs_volume.commit()
            return {"error": "No patches_json generated"}

    soft_timeout = MODAL_TIMEOUT - timeout_buffer_seconds
    print(f"Soft timeout: {soft_timeout}s")

    result = {"repo": repo_name, "repo_id": repo_id}

    try:
        generate_main(
            repo=repo_id,
            max_bugs=max_bugs,
            seed=24,
            interleave=interleave,
            max_entities=max_entities,
            max_candidates=max_candidates,
            timeout_seconds=soft_timeout,
        )
    except Exception as e:
        import traceback

        print(f"Error in generate_main: {e}")
        traceback.print_exc()
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        print("\nCollecting and saving results to volume...")

        collection_result = _safe_execute(
            save_results_to_volume, "Error saving results"
        )
        if collection_result:
            result.update(collection_result)
        else:
            result["error"] = "Failed to collect results"

        # Save log to volume
        log_content = log_buffer.getvalue()
        try:
            volume_bug_dir.mkdir(parents=True, exist_ok=True)
            (volume_bug_dir / "modal_output.log").write_text(log_content)
        except Exception as e:
            print(f"Failed to save log: {e}")

        # If there was an error, write error file
        if "error" in result:
            try:
                (volume_bug_dir / "error.txt").write_text(
                    f"Bug generation failed: {result['error']}"
                )
            except:
                pass

        # Commit volume changes
        logs_volume.commit()

    return result


# ============================================================================
# Validation Sandbox
# ============================================================================
async def run_validation_in_sandbox(
    semaphore: asyncio.Semaphore,
    app: modal.App,
    image_name: str,
    instance_id: str,
    test_cmd: str,
    workdir: str,
    patch: str | None,
    timeout: int,
    postgold_config: dict | None = None,
) -> dict:
    """
    Run validation in a Modal Sandbox with a specific Docker image.

    If postgold_config is provided, runs the remote validator script and returns
    summary metadata. Results are written directly to the volume.

    If postgold_config is None, runs generic test cmd and returns output.
    """
    async with semaphore:
        # print(f"[{instance_id}] Getting validator image ({image_name})...")
        validator_image = get_validator_image(image_name)

        script_lines = [
            "#!/bin/bash",
            "exec 2>&1",
            "set -uxo pipefail",
            f"cd {workdir}",
            "git checkout .",
        ]

        if patch:
            script_lines.extend(
                [
                    f"cat > /tmp/{instance_id}.diff << 'PATCH_EOF'",
                    patch,
                    "PATCH_EOF",
                    f"git apply /tmp/{instance_id}.diff",
                ]
            )

        # Prepare Sandbox arguments
        sandbox_kwargs = {
            "app": app,
            "image": validator_image,
            "timeout": timeout,
        }

        if postgold_config:
            # Mount logs volume for direct writing
            sandbox_kwargs["volumes"] = {LOGS_MOUNT_PATH: logs_volume}

            # Write config and validator script
            config_json = json.dumps(postgold_config)
            script_lines.extend(
                [
                    "cat > /tmp/config.json << 'CONFIG_EOF'",
                    config_json,
                    "CONFIG_EOF",
                    "cat > /tmp/validator.py << 'SCRIPT_EOF'",
                    REMOTE_VALIDATOR_SCRIPT,
                    "SCRIPT_EOF",
                    "python3 /tmp/validator.py /tmp/config.json",
                ]
            )
        else:
            # Legacy/Pregold mode: just run test
            script_lines.extend(
                [
                    f": '{TEST_OUTPUT_START}'",
                    f"{test_cmd} || true",
                    f": '{TEST_OUTPUT_END}'",
                ]
            )

        sb = None
        sandbox_id = None  # Track sandbox ID for debugging
        current_step = "init"  # Track current step for error reporting

        # Debug logging helper
        import time

        debug_sandbox = True  # Set to True to enable detailed sandbox logging

        def _log(step: str, msg: str = ""):
            nonlocal current_step
            current_step = step
            if debug_sandbox:
                ts = time.strftime("%H:%M:%S")
                extra = f" - {msg}" if msg else ""
                print(f"[{ts}][{instance_id}] {step}{extra}")

        try:
            # Rate limit sandbox creation (Modal limit: 5/s)
            _log("rate_limit", "acquiring...")
            await _sandbox_rate_limiter.acquire()
            _log("rate_limit", "acquired")

            # Create sandbox
            _log("create_sandbox", f"image={image_name}, timeout={timeout}s")
            sb = await modal.Sandbox.create.aio(**sandbox_kwargs)
            sandbox_id = getattr(sb, "object_id", None) or getattr(
                sb, "_object_id", "unknown"
            )
            _log("create_sandbox", f"created (sandbox_id={sandbox_id})")

            # Write script to file directly using sandbox.open() to avoid ARG_MAX limit
            script_content = "\n".join(script_lines)
            script_size = len(script_content)

            # Write script file directly to sandbox filesystem (more robust than stdin)
            _log("write_script", f"opening /tmp/run.sh ({script_size} bytes)")
            f = await sb.open.aio("/tmp/run.sh", "w")
            _log("write_script", "writing content")
            await f.write.aio(script_content)
            _log("write_script", "closing file")
            await f.close.aio()
            _log("write_script", "done")

            # Execute the script
            _log("exec_script", "starting bash /tmp/run.sh")
            # Read raw bytes from Modal so repo/build output with non-UTF-8 bytes
            # doesn't fail inside the SDK before we can decode it defensively here.
            process = await sb.exec.aio("bash", "/tmp/run.sh", text=False)
            _log("exec_script", "process started")

            _log("read_stdout", "reading...")
            output_raw = await process.stdout.read.aio()
            output_size = len(output_raw) if output_raw else 0
            _log("read_stdout", f"done ({output_size} bytes)")

            _log("wait_exit", "waiting for exit code...")
            exit_code = await process.wait.aio()
            _log("wait_exit", f"exit_code={exit_code}")
            output = (
                output_raw.decode("utf-8", errors="replace")
                if isinstance(output_raw, bytes)
                else output_raw
            )
            # print(f'{output=}')

            if postgold_config:
                # Parse JSON result from output
                if "<<RESULT_JSON>>" in output:
                    try:
                        json_str = output.split("<<RESULT_JSON>>")[1]
                        result = json.loads(json_str)
                        # Ensure error is propagated if script failed but printed JSON
                        if result.get("exit_code", 0) != 0 and not result.get("error"):
                            # This usually shouldn't happen with our script unless test failed (which is normal)
                            # But let's trust the 'valid' flag and 'error' field
                            pass
                        return result
                    except Exception as e:
                        return {
                            "instance_id": instance_id,
                            "error": f"Failed to parse remote result: {e}",
                            "raw_output": output,
                            "step": current_step,
                            "sandbox_id": sandbox_id,
                        }
                else:
                    return {
                        "instance_id": instance_id,
                        "error": "No remote result found",
                        "raw_output": output,
                        "step": current_step,
                        "sandbox_id": sandbox_id,
                    }
            else:
                return {
                    "instance_id": instance_id,
                    "output": output,
                    "exit_code": exit_code,
                }
        except Exception as e:
            err_str = str(e)
            _log("exception", f"ERROR: {err_str[:200]}")
            return {
                "instance_id": instance_id,
                "error": err_str[:2000],
                "step": current_step,
                "sandbox_id": sandbox_id,
            }
        finally:
            # Always terminate sandbox to prevent zombie connections
            if sb is not None:
                try:
                    await sb.terminate.aio()
                except Exception:
                    pass  # Ignore errors during cleanup


# ============================================================================
# Generation Phase (using Modal .map() for true parallel processing)
# ============================================================================


async def run_generation_phase(repos: list[str], args, language: str) -> list[dict]:
    """Run bug generation for all repos in parallel using Modal .map().

    Uses Modal's .map() for true parallel processing with autoscaling workers.
    Each worker saves results directly to the Volume, reducing data transfer.
    Returns lightweight summaries.
    """
    print(f"{'#' * 60}")
    print(f"# PHASE 1: BUG GENERATION ({len(repos)} repos)")
    print(f"{'#' * 60}\n")

    # Prepare inputs: resolve profiles and filter already-processed repos
    repo_inputs = []  # List of (repo_name, repo_id) tuples for repos to process
    skipped_done = 0
    skipped_error = 0
    failed_to_resolve = []  # Repos that failed profile resolution

    # First, resolve all profiles (can be done in parallel too, but usually fast)
    resolved_repos = []  # List of (repo, repo_id) tuples
    for repo in repos:
        try:
            profile = resolve_profile(repo)
            resolved_repos.append((repo, profile.repo_name))
        except Exception as e:
            failed_to_resolve.append(
                {
                    "repo": repo,
                    "repo_id": None,
                    "error": f"Failed to resolve profile: {e}",
                }
            )

    # Parallelize volume existence checks using asyncio
    # Each repo needs 3 checks: done.txt, error.txt, patches.json

    async def check_repo_status(repo_tuple: tuple[str, str]) -> tuple[str, str, str]:
        """Check if a repo is already processed. Returns (repo, repo_id, status)."""
        repo, repo_id = repo_tuple
        volume_bug_dir = f"{language}/bug_gen/{repo_id}"

        if await volume_file_exists(f"{volume_bug_dir}/done.txt"):
            return (repo, repo_id, "done")
        elif await volume_file_exists(f"{volume_bug_dir}/error.txt"):
            return (repo, repo_id, "error")
        elif await volume_file_exists(f"{language}/bug_gen/{repo_id}_all_patches.json"):
            return (repo, repo_id, "patches_exist")
        else:
            return (repo, repo_id, "pending")

    print(f"  Checking {len(resolved_repos)} repos for existing results (parallel)...")

    semaphore = asyncio.Semaphore(100)

    async def check_with_sem(repo_tuple):
        async with semaphore:
            return await check_repo_status(repo_tuple)

    tasks = [check_with_sem(rt) for rt in resolved_repos]
    if tasks:
        results = await asyncio.gather(*tasks)
    else:
        results = []

    for repo, repo_id, status in results:
        if status == "done":
            print(f"  Skipping {repo}: already completed")
            skipped_done += 1
        elif status == "error":
            print(f"  Skipping {repo}: previously failed")
            skipped_error += 1
        elif status == "patches_exist":
            print(f"  Skipping {repo}: patches already exist")
            skipped_done += 1
        else:
            repo_inputs.append((repo, repo_id))

    if skipped_done or skipped_error:
        print(f"\nSkipped {skipped_done} completed, {skipped_error} failed repos\n")

    if not repo_inputs and not failed_to_resolve:
        print("All repos already processed!\n")
        return []

    repo_names = [r[0] for r in repo_inputs]

    print(f"Running {len(repo_names)} generation tasks with Modal .map()...\n")

    # Use Modal .map() for true parallel processing with autoscaling
    # Each worker saves results directly to Volume; we just collect summaries
    generation_results = list(
        failed_to_resolve
    )  # Start with failed profile resolutions

    if repo_names:
        completed = 0
        total_bugs = 0

        async for result_or_exc in generate_bugs_remote.map.aio(
            repo_names,
            kwargs={
                "max_bugs": args.max_bugs,
                "interleave": args.interleave,
                "max_entities": args.max_entities,
                "max_candidates": args.max_candidates,
                "language": language,  # Workers save directly to Volume
            },
            return_exceptions=True,
            # Future-proof against Modal's deprecation warning.
            wrap_returned_exceptions=False,
        ):
            completed += 1

            if isinstance(result_or_exc, Exception):
                # Worker crashed - result already includes repo info from the exception context
                generation_results.append(
                    {"error": f"Worker exception: {result_or_exc}"}
                )
                print(f"  [{completed}/{len(repo_names)}] ERROR: {result_or_exc}")
            else:
                # Result is a dict with repo, repo_id, total_bugs/patches/error
                generation_results.append(result_or_exc)
                repo = result_or_exc.get("repo", "unknown")
                if "error" in result_or_exc:
                    print(
                        f"  [{completed}/{len(repo_names)}] {repo}: ERROR - {result_or_exc['error'][:50]}"
                    )
                else:
                    bugs = result_or_exc.get("total_bugs", 0)
                    total_bugs += bugs
                    print(
                        f"  [{completed}/{len(repo_names)}] {repo}: {bugs} bugs generated"
                    )

        print(
            f"\nGeneration complete: {total_bugs} total bugs from {len(repo_names)} repos\n"
        )

    return generation_results


# ============================================================================
# Validation Phase
# ============================================================================


def annotate_patches(
    patches: list, repo: str, repo_id: str, profile, language: str
) -> list:
    """Add metadata to patches for validation."""
    for p in patches:
        p["_repo"] = repo
        p["_repo_id"] = repo_id
        p["_profile"] = profile
        p["_language"] = language
    return patches


async def collect_patches_from_files(repos: list[str], language: str) -> list[dict]:
    """Collect patches from Modal Volume for validate-only mode."""
    import re

    all_patches = []

    # First, resolve all profiles (usually fast, local operation)
    resolved_repos = []  # List of (repo, repo_id, profile) tuples
    for repo in repos:
        try:
            profile = resolve_profile(repo)
            resolved_repos.append((repo, profile.repo_name, profile))
        except Exception:
            print(f"  Skipping {repo}: profile not found")

    async def check_and_load_repo(repo_tuple: tuple) -> tuple:
        """Check repo status and load patches if valid. Returns (repo, repo_id, profile, status, patches_json)."""
        repo, repo_id, profile = repo_tuple
        bug_gen_dir = f"{language}/bug_gen/{repo_id}"

        # 1. Check if validation previously failed (broken baseline)
        if await volume_file_exists(
            f"{language}/run_validation/{repo_id}/{repo_id}.ref/error.txt"
        ):
            return (repo, repo_id, profile, "validation_failed", None)

        # 2. Check if generation failed
        if await volume_file_exists(f"{bug_gen_dir}/error.txt"):
            return (repo, repo_id, profile, "generation_failed", None)

        # 3. Check patch count from done.txt to avoid reading large files for small repos
        done_content = await volume_read_text(f"{bug_gen_dir}/done.txt")
        if done_content:
            match = re.search(r"completed: (\d+) bugs", done_content)
            if match:
                count = int(match.group(1))
                if count < MIN_PATCHES_FOR_VALIDATION:
                    return (repo, repo_id, profile, f"too_few_patches:{count}", None)

        # 4. Read patches
        patches_path = f"{language}/bug_gen/{repo_id}_all_patches.json"
        patches_json = await volume_read_text(patches_path)

        if patches_json:
            return (repo, repo_id, profile, "ok", patches_json)
        else:
            return (repo, repo_id, profile, "no_patches_file", None)

    print(f"  Checking {len(resolved_repos)} repos for patches (parallel)...")

    semaphore = asyncio.Semaphore(100)

    async def check_with_sem(rt):
        async with semaphore:
            return await check_and_load_repo(rt)

    tasks = [check_with_sem(rt) for rt in resolved_repos]
    if tasks:
        results = await asyncio.gather(*tasks)
    else:
        results = []

    for repo, repo_id, profile, status, patches_json in results:
        if status == "validation_failed":
            print(f"  Skipping {repo}: validation previously failed (pre-gold)")
        elif status == "generation_failed":
            print(f"  Skipping {repo}: bug generation failed")
        elif status.startswith("too_few_patches:"):
            count = status.split(":")[1]
            print(
                f"  Skipping {repo}: too few patches ({count} < {MIN_PATCHES_FOR_VALIDATION})"
            )
        elif status == "no_patches_file":
            print(f"  Skipping {repo}: no patches file")
        elif status == "ok" and patches_json:
            patches = json.loads(patches_json)
            all_patches.extend(
                annotate_patches(patches, repo, repo_id, profile, language)
            )
            print(f"  {repo}: {len(patches)} patches")

    return all_patches


def collect_patches_from_generation(
    generation_results: list[dict], language: str
) -> tuple[list[dict], list[dict]]:
    """Collect patches from generation results, separating errors."""
    all_patches, errors = [], []
    for gen_result in generation_results:
        if "error" in gen_result:
            errors.append(gen_result)
            continue
        patches = gen_result.get("patches", [])
        if patches:
            profile = resolve_profile(gen_result["repo"])
            all_patches.extend(
                annotate_patches(
                    patches,
                    gen_result["repo"],
                    gen_result["repo_id"],
                    profile,
                    language,
                )
            )
    return all_patches, errors


def build_repos_with_patches(all_patches: list) -> dict:
    """Build repos_with_patches dict from annotated patches."""
    repos = {}
    for p in all_patches:
        repo = p["_repo"]
        if repo not in repos:
            repos[repo] = {
                "profile": p["_profile"],
                "repo_id": p["_repo_id"],
                "language": p["_language"],
            }
    return repos


async def run_pregold_phase_async(
    repos_with_patches: dict,
    max_concurrent: int,
    env_name: str,
    baseline_timeout: int = PREGOLD_TIMEOUT,
) -> set[str]:
    """Run all pre-gold (baseline) tests asynchronously. Returns set of repos with 0 passing tests (to skip)."""
    import tempfile
    from swesmith.harness.grading import read_test_output
    from swebench.harness.constants import TestStatus

    print("\nPHASE: PRE-GOLD (BASELINE) TESTS")
    print(
        f"Running {len(repos_with_patches)} baselines, max concurrent: {max_concurrent}"
    )

    tasks = []
    previously_failed = set()  # Repos that failed in previous runs

    # Parallelize volume existence checks using asyncio

    async def check_baseline_status(repo_info_tuple: tuple) -> tuple[str, dict, str]:
        """Check if baseline exists or failed. Returns (repo, info, status)."""
        repo, info = repo_info_tuple
        lang = info["language"]
        baseline_output_path = f"{lang}/run_validation/{info['repo_id']}/{info['repo_id']}.ref/test_output.txt"
        error_path = (
            f"{lang}/run_validation/{info['repo_id']}/{info['repo_id']}.ref/error.txt"
        )

        test_output_exists = await volume_file_exists(baseline_output_path)
        error_exists = await volume_file_exists(error_path)

        if test_output_exists and not error_exists:
            return (repo, info, "exists")
        elif error_exists:
            return (repo, info, "failed")
        else:
            return (repo, info, "pending")

    print(
        f"  Checking {len(repos_with_patches)} baselines for existing results (parallel)..."
    )

    semaphore = asyncio.Semaphore(100)

    async def check_with_sem(item):
        async with semaphore:
            return await check_baseline_status(item)

    check_tasks = [
        check_with_sem((repo, info)) for repo, info in repos_with_patches.items()
    ]
    if check_tasks:
        results = await asyncio.gather(*check_tasks)
    else:
        results = []

    for repo, info, status in results:
        if status == "exists":
            print(f"  Skipping {repo}: baseline exists")
        elif status == "failed":
            print(f"  Skipping {repo}: previously failed")
            previously_failed.add(repo)
        else:
            tasks.append(
                {
                    "repo": repo,
                    "repo_id": info["repo_id"],
                    "profile": info["profile"],
                    "instance_id": f"{info['repo_id']}.ref",
                    "workdir": f"/{env_name}",
                    "language": info["language"],
                }
            )

    if not tasks:
        print("  All baselines already exist!\\n")
        return previously_failed  # Return previously failed repos to skip in post-gold

    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)
    failed_repos = previously_failed.copy()  # Start with previously failed repos

    # Install custom exception handler to log socket.send() exception details
    loop = asyncio.get_running_loop()
    exception_handler = setup_asyncio_exception_logging()
    loop.set_exception_handler(exception_handler)

    async def process_baseline(task: dict) -> tuple[dict, dict]:
        """Process a single baseline test."""
        result = await run_validation_in_sandbox(
            semaphore=semaphore,
            app=app,
            image_name=task["profile"].image_name,
            instance_id=task["instance_id"],
            test_cmd=task["profile"].test_cmd,
            workdir=task["workdir"],
            patch=None,
            timeout=baseline_timeout,
        )
        return (task, result)

    # Create all async tasks
    async_tasks = [process_baseline(t) for t in tasks]

    # Process results as they complete
    completed = 0
    for coro in asyncio.as_completed(async_tasks):
        task, result = await coro
        completed += 1

        lang = task["language"]
        volume_baseline_dir = (
            f"{lang}/run_validation/{task['repo_id']}/{task['instance_id']}"
        )

        try:
            if "error" not in result:
                # Save output to volume
                await volume_write_text(
                    f"{volume_baseline_dir}/test_output.txt", result["output"]
                )

                # Validate baseline has at least 1 passing test (use temp file for parsing)
                try:
                    with tempfile.NamedTemporaryFile(
                        mode="w", suffix=".txt", delete=False
                    ) as f:
                        f.write(result["output"])
                        temp_path = f.name
                    test_output, found = read_test_output(temp_path)
                    Path(temp_path).unlink()

                    if found and test_output:
                        status_map = task["profile"].log_parser(test_output)
                        passed = sum(
                            1
                            for s in status_map.values()
                            if s == TestStatus.PASSED.value
                        )
                        if passed == 0:
                            status = "⚠️ 0 tests passed (skipping post-gold)"
                            failed_repos.add(task["repo"])
                            await volume_write_text(
                                f"{volume_baseline_dir}/error.txt",
                                "Pre-gold failed: 0 tests passed",
                            )
                        else:
                            status = f"OK ({passed} tests passed)"
                    else:
                        # Diagnose why test output wasn't found
                        raw_output = result["output"]
                        if (
                            "APPLY_PATCH_FAIL" in raw_output
                            or "error: patch failed" in raw_output
                        ):
                            reason = "patch apply failed"
                        elif TEST_OUTPUT_START not in raw_output:
                            reason = "test command crashed before start marker"
                        elif TEST_OUTPUT_END not in raw_output:
                            reason = "tests never completed (no end marker)"
                        elif not test_output:
                            reason = "no test output between markers"
                        else:
                            reason = "unknown"
                        status = f"⚠️ {reason} (skipping post-gold)"
                        failed_repos.add(task["repo"])
                        await volume_write_text(
                            f"{volume_baseline_dir}/error.txt",
                            f"Pre-gold failed: {reason}",
                        )
                except Exception as e:
                    status = f"OK (parse check failed: {e})"
            else:
                status = f"ERROR: {result['error'][:50]}"
                failed_repos.add(task["repo"])
                await volume_write_text(
                    f"{volume_baseline_dir}/error.txt",
                    f"Pre-gold sandbox error: {result['error']}",
                )
        except Exception as e:
            status = f"EXCEPTION: {e}"
            failed_repos.add(task["repo"])
            try:
                await volume_write_text(
                    f"{volume_baseline_dir}/error.txt", f"Pre-gold exception: {e}"
                )
            except:
                pass
        print(f"  [{completed}/{len(tasks)}] {task['repo']}: {status}")

    print(f"Pre-gold complete: {completed} baselines")
    if failed_repos:
        print(f"  ⚠️ {len(failed_repos)} repos will be skipped in post-gold")
    print()
    return failed_repos


async def run_postgold_phase_async(
    all_patches: list,
    max_concurrent: int,
    env_name: str,
    baseline_texts: dict[str, str] | None = None,
    validation_timeout_override: int | None = None,
) -> list[dict]:
    """
    Run all post-gold tests using asyncio for efficient concurrent I/O.

    Uses asyncio.Semaphore to limit concurrency instead of ThreadPoolExecutor.
    This is much more efficient for I/O-bound operations like Modal API calls:
    - ThreadPoolExecutor with 1000 workers = 1000 threads = high memory/CPU overhead
    - asyncio with semaphore = 1 thread + event loop = minimal overhead
    """

    print("PHASE: POST-GOLD TESTS")
    print(f"Running {len(all_patches)} patches, max concurrent: {max_concurrent}")

    # Parallelize volume existence checks to avoid slow sequential roundtrips using asyncio

    async def check_patch_completion(p):
        path = f"{p['_language']}/run_validation/{p['_repo_id']}/{p['instance_id']}/report.json"
        return p, await volume_file_exists(path)

    print(f"  Checking {len(all_patches)} patches for existing results (parallel)...")
    tasks = []

    checkout_sem = asyncio.Semaphore(100)  # Limit concurrent checks against volume

    async def check_with_sem(p):
        async with checkout_sem:
            return await check_patch_completion(p)

    check_tasks = [check_with_sem(p) for p in all_patches]
    if check_tasks:
        results = await asyncio.gather(*check_tasks)
    else:
        results = []

    for p, exists in results:
        if not exists:
            tasks.append(
                {
                    "repo": p["_repo"],
                    "repo_id": p["_repo_id"],
                    "profile": p["_profile"],
                    "instance_id": p["instance_id"],
                    "patch": p["patch"],
                    "workdir": f"/{env_name}",
                    "full_patch": p,
                }
            )

    print(
        f"  {len(all_patches) - len(tasks)} already validated, {len(tasks)} remaining"
    )

    if not tasks:
        print("  All patches already validated!")
        return []

    # Semaphore controls max concurrent operations
    semaphore = asyncio.Semaphore(max_concurrent)

    # Install custom exception handler to log socket.send() exception details
    loop = asyncio.get_running_loop()
    exception_handler = setup_asyncio_exception_logging()
    loop.set_exception_handler(exception_handler)

    async def process_single_task(task: dict) -> dict:
        """Process a single validation task."""
        lang = task["full_patch"]["_language"]
        repo_id = task["repo_id"]
        instance_id = task["instance_id"]

        # Strip internal keys (prefixed with _) that contain non-serializable objects like the profile
        serializable_patch = {
            k: v for k, v in task["full_patch"].items() if not k.startswith("_")
        }

        # Volume path for report (used for both success and failure)
        report_volume_path = (
            f"{lang}/run_validation/{repo_id}/{instance_id}/report.json"
        )
        # Write patch file to volume (required for gather step)
        await volume_write_text(
            f"{lang}/run_validation/{repo_id}/{instance_id}/patch.diff",
            task["patch"],
        )

        postgold_config = {
            "test_cmd": task["profile"].test_cmd,
            "output_path": f"/logs/{lang}/run_validation/{repo_id}/{instance_id}/test_output.txt",
            "baseline_path": f"/logs/{lang}/run_validation/{repo_id}/{repo_id}.ref/test_output.txt",
            "report_path": f"/logs/{lang}/run_validation/{repo_id}/{instance_id}/report.json",
            "baseline_text": (baseline_texts or {}).get(repo_id),
            "instance": serializable_patch,
        }

        timeout = (
            validation_timeout_override
            if validation_timeout_override is not None
            else task["profile"].timeout
        )

        result = await run_validation_in_sandbox(
            semaphore=semaphore,
            app=app,
            image_name=task["profile"].image_name,
            instance_id=task["instance_id"],
            test_cmd=task["profile"].test_cmd,
            workdir=task["workdir"],
            patch=task["patch"],
            timeout=timeout,
            postgold_config=postgold_config,
        )

        # If validation failed (error in result), write a report.json anyway
        # so this patch won't be retried on subsequent runs
        if "error" in result and result.get("error"):
            error_report = {
                "instance_id": instance_id,
                "valid": False,
                "error": result["error"],
                "PASS_TO_FAIL": [],
                "FAIL_TO_PASS": [],
                "skipped": True,  # Mark as skipped so we know it wasn't a real validation
            }
            try:
                await volume_write_text(
                    report_volume_path, json.dumps(error_report, indent=2)
                )
            except Exception as write_err:
                print(f"Failed to write error report for {instance_id}: {write_err}")

        return (task, result)

    # Create all async tasks
    async_tasks = [process_single_task(t) for t in tasks]

    # Track progress
    results = []
    completed = 0
    valid_count = 0

    # Process results as they complete
    for coro in asyncio.as_completed(async_tasks):
        task, result = await coro
        completed += 1

        processed = result
        processed["repo"] = task["repo"]
        # result already has instance_id, valid, error keys from the sandbox return

        results.append(processed)
        if processed.get("valid"):
            valid_count += 1
        if completed % 100 == 0 or completed == len(tasks):
            print(
                f"  Progress: {completed}/{len(tasks)} tests, {valid_count} valid bugs"
            )

    print(f"Post-gold complete: {valid_count}/{len(tasks)} valid bugs\n")
    return results


async def run_validation_phase_async(
    all_patches: list,
    max_concurrent: int,
    env_name: str,
    validation_timeout_override: int | None = None,
) -> list[dict]:
    """Run complete validation (pre-gold + post-gold). Existing baselines are skipped automatically."""
    if not all_patches:
        print("No patches to validate.")
        return []

    # Count patches per repo and filter out repos with too few patches
    repo_patch_counts = {}
    for p in all_patches:
        repo = p["_repo"]
        repo_patch_counts[repo] = repo_patch_counts.get(repo, 0) + 1

    small_repos = {
        repo
        for repo, count in repo_patch_counts.items()
        if count < MIN_PATCHES_FOR_VALIDATION
    }
    if small_repos:
        original_count = len(all_patches)
        all_patches = [p for p in all_patches if p["_repo"] not in small_repos]
        print(
            f"Skipping {len(small_repos)} repos with <{MIN_PATCHES_FOR_VALIDATION} patches: {', '.join(sorted(small_repos))}"
        )
        print(f"Filtered out {original_count - len(all_patches)} patches\n")

    if not all_patches:
        print("No patches remaining after filtering.")
        return []

    repos_with_patches = build_repos_with_patches(all_patches)

    # Pre-build all validator images before starting validation
    await prebuild_validator_images_async(repos_with_patches)

    failed_repos = await run_pregold_phase_async(
        repos_with_patches,
        max_concurrent,
        env_name,
        baseline_timeout=(
            validation_timeout_override
            if validation_timeout_override is not None
            else PREGOLD_TIMEOUT
        ),
    )

    lang = all_patches[0]["_language"] if all_patches else ""
    baseline_texts = {}
    for repo, info in repos_with_patches.items():
        if repo in failed_repos:
            continue
        baseline_text = await volume_read_text(
            f"{lang}/run_validation/{info['repo_id']}/{info['repo_id']}.ref/test_output.txt"
        )
        if baseline_text:
            baseline_texts[info["repo_id"]] = baseline_text

    # Filter out patches from repos with broken baselines
    if failed_repos:
        original_count = len(all_patches)
        all_patches = [p for p in all_patches if p["_repo"] not in failed_repos]
        print(
            f"Filtered out {original_count - len(all_patches)} patches from {len(failed_repos)} repos with broken baselines"
        )

    return await run_postgold_phase_async(
        all_patches,
        max_concurrent,
        env_name,
        baseline_texts=baseline_texts,
        validation_timeout_override=validation_timeout_override,
    )


def print_summary(results: list[dict], repos_count: int):
    """Print validation summary."""
    valid_count = sum(1 for r in results if r.get("valid"))

    print(f"\n{'=' * 60}")
    print(f"RESULTS: {valid_count} valid bugs out of {len(results)} patches")
    print(f"{'=' * 60}")

    repo_stats = {}
    for r in results:
        repo = r["repo"]
        if repo not in repo_stats:
            repo_stats[repo] = {"total": 0, "valid": 0, "errors": 0}
        repo_stats[repo]["total"] += 1
        if r.get("valid"):
            repo_stats[repo]["valid"] += 1
        if r.get("error"):
            repo_stats[repo]["errors"] += 1

    print("\nPer-repo breakdown:")
    for repo, stats in sorted(repo_stats.items()):
        err = f" ({stats['errors']} errors)" if stats["errors"] else ""
        print(f"  {repo}: {stats['valid']}/{stats['total']} valid{err}")

    print(
        f"\nTotal: {valid_count}/{len(results)} valid bugs across {repos_count} repos"
    )


# ============================================================================
# Gather Phase (Create Task Instances & Push Branches)
# ============================================================================


@app.function(
    image=generator_image,
    secrets=[modal.Secret.from_name("GITHUB_TOKEN")],
    # Gather can push hundreds of branches for large repos; 10 minutes is too low.
    timeout=60 * MINUTES,
    volumes={LOGS_MOUNT_PATH: logs_volume},
)
def gather_remote(
    repo_name: str,
    language: str,
    repush_image: bool = False,
    override_branch: bool = False,
) -> dict:
    """Run gather.py for a repository to create task instances and push branches."""
    import os
    import subprocess
    import traceback
    from pathlib import Path

    # Ensure swesmith is in path
    if "/root" not in sys.path:
        sys.path.append("/root")

    from swesmith.profiles import registry

    # Resolve repo ID
    def resolve_repo_id():
        try:
            return registry.get_from_inst(
                {"repo": repo_name, "instance_id": "dummy"}
            ).repo_name
        except Exception:
            target = repo_name.replace("/", "__")
            candidates = [key for key in registry.keys() if target in key]
            return candidates[0] if candidates else repo_name

    repo_id = resolve_repo_id()
    print(f"Gathering for {repo_name} (ID: {repo_id})")

    # Setup environment to satisfy gather.py expectations
    # 1. gather.py expects logs/run_validation to contain the repo logs
    # 2. gather.py writes to logs/task_insts

    work_dir = Path("/root")
    logs_link_dir = work_dir / "logs"
    logs_link_dir.mkdir(exist_ok=True)

    # Configure git authentication
    if "GITHUB_TOKEN" in os.environ:
        token = os.environ["GITHUB_TOKEN"]
        print(f"DEBUG: Found GITHUB_TOKEN (len={len(token)}). Configuring git auth...")

        # Use simpler authenticated URL format for PATs
        subprocess.run(
            [
                "git",
                "config",
                "--global",
                f"url.https://{token}@github.com/.insteadOf",
                "https://github.com/",
            ],
            check=True,
        )
        # Also configure user info
        subprocess.run(
            ["git", "config", "--global", "user.email", "swesmith@swesmith.ai"],
            check=False,
        )
        subprocess.run(
            ["git", "config", "--global", "user.name", "swesmith"], check=False
        )
    else:
        print("Warning: GITHUB_TOKEN not found in environment. Git push may fail.")

    # Link run_validation: logs/run_validation -> /logs/{language}/run_validation
    # We use the mounted volume path directly as the target
    validation_source = Path(LOGS_MOUNT_PATH) / language / "run_validation"
    validation_link = logs_link_dir / "run_validation"

    # Link task_insts: logs/task_insts -> /logs/task_insts (volume root)
    task_insts_source = Path(LOGS_MOUNT_PATH) / language / "task_insts"
    task_insts_link = logs_link_dir / "task_insts"

    try:
        # Ensure sources exist on volume
        task_insts_source.mkdir(parents=True, exist_ok=True)
        if not validation_source.exists():
            return {
                "repo": repo_name,
                "status": "skipped",
                "reason": "No validation logs",
            }

        # Create symlinks
        if not validation_link.exists():
            os.symlink(str(validation_source), str(validation_link))

        if not task_insts_link.exists():
            os.symlink(str(task_insts_source), str(task_insts_link))

        # Check if there are actually validation logs for this repo
        repo_vals = validation_link / repo_id
        if not repo_vals.exists():
            return {
                "repo": repo_name,
                "status": "skipped",
                "reason": "No logs for repo",
            }

        # Build command
        # python -m swesmith.harness.gather logs/run_validation/<repo_id>
        cmd = [
            sys.executable,
            "-m",
            "swesmith.harness.gather",
            str(Path("logs/run_validation") / repo_id),
            "-v",
            "-d",
        ]

        if repush_image:
            cmd.append("--repush_image")
        if override_branch:
            cmd.append("--override_branch")

        print(f"Running: {' '.join(cmd)}")

        # execution
        result = subprocess.run(
            cmd, cwd=str(work_dir), capture_output=True, text=True, env=os.environ
        )

        if result.returncode != 0:
            print("Gather failed:")
            print(result.stdout)
            print(result.stderr)
            return {
                "repo": repo_name,
                "status": "failed",
                "stdout": result.stdout,
                "stderr": result.stderr,
            }
        else:
            print("Gather succeeded:")
            print(result.stdout)
            print(result.stderr)

        return {
            "repo": repo_name,
            "status": "success",
            "stdout": result.stdout,
            "stderr": result.stderr,
        }

    except Exception as e:
        traceback.print_exc()
        return {"repo": repo_name, "status": "error", "error": str(e)}


async def run_gather_phase_async(repos: list[str], language: str, args) -> None:
    """Run gather phase for all repos in parallel."""
    print(f"\n{'#' * 60}")
    print(f"# PHASE 3: GATHER ({len(repos)} repos)")
    print(f"{'#' * 60}\n")

    # We can pass repush_image and override_branch via args if they existed,
    # but for now we'll assume defaults or add them to args class if needed.
    repush = getattr(args, "repush_image", False)
    override = getattr(args, "override_branch", False)

    completed = 0
    success = 0

    print(f"Starting gather for {len(repos)} repos...")

    async for result in gather_remote.map.aio(
        repos,
        kwargs={
            "language": language,
            "repush_image": repush,
            "override_branch": override,
        },
    ):
        completed += 1
        repo = result.get("repo", "unknown")
        status = result.get("status", "unknown")

        if status == "success":
            success += 1
            print(f"  [{completed}/{len(repos)}] {repo}: Success")
            # Print last few lines of stdout to see "Wrote X instances"
            if "stdout" in result:
                lines = result["stdout"].splitlines()
                for line in lines[-5:]:
                    print(f"    | {line}")
        elif status == "skipped":
            print(
                f"  [{completed}/{len(repos)}] {repo}: Skipped ({result.get('reason')})"
            )
        else:
            err = result.get("error") or "Non-zero exit code"
            print(f"  [{completed}/{len(repos)}] {repo}: Failed - {err}")

    print(f"\nGather complete: {success}/{len(repos)} repos processed successfully.\n")


# ============================================================================
# Issue Generation
# ============================================================================


@app.function(
    image=generator_image,
    volumes={LOGS_MOUNT_PATH: logs_volume},
    timeout=3600,
    secrets=[
        modal.Secret.from_name("GITHUB_TOKEN"),
        modal.Secret.from_name("PORTKEY_API_KEY"),
    ],
)
def issue_gen_remote(
    repo: str,
    language: str,
    config: str,
    workers: int,
) -> dict:
    """Generate issue descriptions for a single repo's task instances.

    Calls the existing swesmith.issue_gen.generate.IssueGen class to generate
    issue descriptions for all task instances in a repo. Uses symlinks to redirect
    local paths to Modal volume paths.

    Args:
        repo: Repository name (e.g., "astropy__astropy")
        language: Programming language filter
        config: Path to config file
        workers: Number of workers per repo
    """
    import os
    from pathlib import Path

    # Set up paths
    volume_root = Path(LOGS_MOUNT_PATH) / language
    task_insts_dir = volume_root / "task_insts"

    # Resolve task instances file (it may have a hash suffix like repo__name.abcdef.json)
    task_insts_file = None
    repo_sanitized = repo.replace("/", "__")

    if task_insts_dir.exists():
        for filename in os.listdir(task_insts_dir):
            # Check for exact match or match with suffix
            if filename == f"{repo_sanitized}.json" or (
                filename.startswith(f"{repo_sanitized}.") and filename.endswith(".json")
            ):
                task_insts_file = task_insts_dir / filename
                break

    # Check if task instances file exists
    if not task_insts_file or not task_insts_file.exists():
        return {
            "success": True,  # Not an error, just nothing to do
            "repo": repo,
            "instances_processed": 0,
            "status": "skipped",
            "reason": "No task insts file",
        }

    # Create symlinks to redirect local paths to volume paths
    # This allows IssueGen to work with its expected local paths
    local_logs = Path("/root/logs")
    local_logs.mkdir(parents=True, exist_ok=True)

    # Symlink the entire logs directory structure
    for subdir in ["task_insts", "run_validation", "issue_gen"]:
        local_subdir = local_logs / subdir
        volume_subdir = volume_root / subdir

        # Create the volume directory if it doesn't exist
        volume_subdir.mkdir(parents=True, exist_ok=True)

        # Create symlink (thread-safe with FileExistsError handling)
        try:
            if local_subdir.exists():
                local_subdir.unlink()
            local_subdir.symlink_to(volume_subdir)
        except FileExistsError:
            # Another concurrent task already created the symlink
            pass

    try:
        # Import IssueGen after symlinks are set up
        from swesmith.issue_gen.generate import IssueGen

        # Verify config file exists
        config_path = Path(config)
        if not config_path.exists():
            return {
                "success": False,
                "repo": repo,
                "error": f"Config file not found: {config}",
            }

        # Set up IssueGen instance
        issue_gen = IssueGen(
            dataset_path=str(task_insts_file),
            config_file=Path(config),
            workers=workers,
            redo_existing=False,
        )

        # Run issue generation
        # This processes all instances in the repo using ThreadPoolExecutor
        issue_gen.run()

        # Count how many instances were processed
        issue_gen_file = volume_root / "issue_gen" / f"{repo}.json"
        instances_processed = 0
        if issue_gen_file.exists():
            import json

            with open(issue_gen_file) as f:
                data = json.load(f)
                instances_processed = len(data)

        return {
            "success": True,
            "repo": repo,
            "instances_processed": instances_processed,
        }

    except Exception as e:
        import traceback

        return {
            "success": False,
            "repo": repo,
            "error": f"{type(e).__name__}: {str(e)}",
            "traceback": traceback.format_exc(),
        }


async def run_issue_gen_phase_async(
    repos: list[str],
    language: str,
    issue_gen_config: str,
    issue_gen_workers: int,
) -> None:
    """Run issue generation phase for all repos in parallel.

    Args:
        repos: List of repository names to process
        language: Programming language filter
        issue_gen_config: Path to config file
        issue_gen_workers: Number of workers per repo
        issue_gen_redo: Whether to regenerate existing issues
    """
    print(f"\n{'=' * 80}")
    print("ISSUE GENERATION PHASE")
    print(f"{'=' * 80}")
    print(f"Processing {len(repos)} repositories...")
    print(f"Config: {issue_gen_config}")
    print(f"Workers per repo: {issue_gen_workers}")
    print()

    # Run issue generation in parallel across all repos
    results = []
    async for result in issue_gen_remote.map.aio(
        repos,
        kwargs={
            "language": language,
            "config": issue_gen_config,
            "workers": issue_gen_workers,
        },
        order_outputs=False,
    ):
        results.append(result)

        # Print progress
        completed = len(results)
        if result["success"]:
            instances = result.get("instances_processed", 0)
            print(
                f"  [{completed}/{len(repos)}] {result['repo']}: ✓ ({instances} instances)"
            )
        else:
            error = result.get("error", "Unknown error")
            print(f"  [{completed}/{len(repos)}] {result['repo']}: ✗ {error}")
            if "traceback" in result:
                print(f"    Traceback: {result['traceback'][:200]}...")

    # Summary
    success = sum(1 for r in results if r["success"])
    total_instances = sum(
        r.get("instances_processed", 0) for r in results if r["success"]
    )

    print(
        f"\nIssue generation complete: {success}/{len(repos)} repos processed successfully."
    )
    print(f"Total instances with issues: {total_instances}\n")


# ============================================================================
# Stats Display
# ============================================================================


async def show_volume_stats(
    language: str, repo_filters: list[str] | None = None
) -> None:
    """Display a bug breakdown by reading validation results from the Modal Volume.

    Similar to count_bugs_to_file.py but reads from Modal Volume instead of local files.
    Uses parallel I/O for faster stats collection.
    """
    print(f"\nReading stats from volume '{VOLUME_NAME}/{language}/'...\n")

    repo_stats: dict[str, dict[str, int]] = {}
    modifier_stats: dict[str, dict[str, int]] = {}  # Track stats by modifier
    semaphore = asyncio.Semaphore(100)  # Limit concurrent reads
    selected_repo_ids: set[str] = set()
    selected_repo_prefixes: set[str] = set()

    if repo_filters:
        for repo_filter in repo_filters:
            repo_filter = repo_filter.strip()
            if not repo_filter:
                continue

            if "__" in repo_filter and "." in repo_filter:
                selected_repo_ids.add(repo_filter)
                continue

            if "__" in repo_filter and "." not in repo_filter:
                selected_repo_prefixes.add(f"{repo_filter}.")
                continue

            if "/" in repo_filter:
                try:
                    selected_repo_ids.add(resolve_profile(repo_filter).repo_name)
                except Exception:
                    selected_repo_prefixes.add(f"{repo_filter.replace('/', '__')}.")
                continue

            selected_repo_prefixes.add(repo_filter)

        print(f"Filtering stats to {len(repo_filters)} repo selector(s)")

    def repo_matches(repo_id: str) -> bool:
        if not selected_repo_ids and not selected_repo_prefixes:
            return True
        if repo_id in selected_repo_ids:
            return True
        return any(repo_id.startswith(prefix) for prefix in selected_repo_prefixes)

    def extract_modifier(instance_id: str) -> str:
        """Extract modifier name from instance_id (format: repo_id.modifier__hash).

        Example instance_id: Shopify__draggable.8a1eed57.func_pm_arg_swap__abc123
        Should extract: func_pm_arg_swap
        """
        # The modifier is the part before the final '__' which is followed by the hash
        # Find the last occurrence of '__' and take what's before it
        if "__" not in instance_id:
            return "unknown"

        # Split by '__' and take the second-to-last part
        # e.g., "repo.commit.func_pm_arg_swap__abc123" -> ["repo.commit.func_pm_arg_swap", "abc123"]
        before_hash = instance_id.rsplit("__", 1)[0]  # "repo.commit.func_pm_arg_swap"

        # The modifier is the last dot-separated part
        # e.g., "repo.commit.func_pm_arg_swap" -> "func_pm_arg_swap"
        if "." in before_hash:
            return before_hash.rsplit(".", 1)[-1]  # Get last part after final '.'
        return before_hash

    # 1. Count generated bugs from patches files (parallel)
    bug_gen_dir = f"{language}/bug_gen"
    try:
        entries = await logs_volume.listdir.aio(bug_gen_dir)
        patch_files = []
        for entry in entries:
            if not entry.path.endswith("_all_patches.json"):
                continue
            repo_id = entry.path.split("/")[-1].replace("_all_patches.json", "")
            if repo_matches(repo_id):
                patch_files.append(entry)

        async def read_patches(entry) -> tuple[str, int, list[dict]]:
            async with semaphore:
                # entry.path is the full path, extract just the filename
                filename = entry.path.split("/")[-1]
                repo_id = filename.replace("_all_patches.json", "")
                # Use entry.path directly as it's the full path
                content = await volume_read_text(entry.path)
                if content:
                    try:
                        patches = json.loads(content)
                        return (repo_id, len(patches), patches)
                    except json.JSONDecodeError:
                        pass
                return (repo_id, 0, [])

        results = await asyncio.gather(*[read_patches(e) for e in patch_files])
        for repo_id, count, patches in results:
            if repo_id not in repo_stats:
                repo_stats[repo_id] = {"generated": 0, "validated": 0, "valid": 0}
            repo_stats[repo_id]["generated"] = count

            # Count generated bugs by modifier
            for patch in patches:
                instance_id = patch.get("instance_id", "")
                modifier = extract_modifier(instance_id)
                if modifier not in modifier_stats:
                    modifier_stats[modifier] = {
                        "generated": 0,
                        "validated": 0,
                        "valid": 0,
                    }
                modifier_stats[modifier]["generated"] += 1

        print(f"  Found {len(patch_files)} repos with patches")
    except Exception as e:
        print(f"Warning: Could not read bug_gen directory: {e}")

    # 2. Count validated bugs from run_validation directory (parallel)
    run_validation_dir = f"{language}/run_validation"
    try:
        repo_entries = await logs_volume.listdir.aio(run_validation_dir)
        repo_entries_filtered = []
        for entry in repo_entries:
            repo_id = entry.path.split("/")[-1]
            if repo_matches(repo_id):
                repo_entries_filtered.append(entry)

        # First, collect all report.json paths to read (with instance_id for modifier extraction)
        all_report_paths: list[
            tuple[str, str, str]
        ] = []  # (repo_id, report_path, instance_id)

        async def list_repo_instances(repo_entry) -> list[tuple[str, str, str]]:
            """List all instance report paths for a repo."""
            async with semaphore:
                # entry.path is full path like "javascript/run_validation/repo_id"
                repo_id = repo_entry.path.split("/")[-1]
                repo_path = repo_entry.path  # Use full path directly
                paths = []
                try:
                    instance_entries = await logs_volume.listdir.aio(repo_path)
                    for instance_entry in instance_entries:
                        # instance_entry.path is full path
                        instance_id = instance_entry.path.split("/")[-1]
                        if not instance_id.endswith(".ref"):
                            report_path = f"{instance_entry.path}/report.json"
                            paths.append((repo_id, report_path, instance_id))
                except Exception:
                    pass
                return paths

        # Gather all report paths in parallel
        path_results = await asyncio.gather(
            *[list_repo_instances(e) for e in repo_entries_filtered]
        )
        for paths in path_results:
            all_report_paths.extend(paths)

        print(f"  Found {len(all_report_paths)} validation reports to check")

        # Initialize repo_stats for all repos
        for repo_entry in repo_entries_filtered:
            repo_id = repo_entry.path.split("/")[-1]
            if repo_id not in repo_stats:
                repo_stats[repo_id] = {"generated": 0, "validated": 0, "valid": 0}

        # Read all reports in parallel
        async def read_report(
            item: tuple[str, str, str],
        ) -> tuple[str, str, bool, bool]:
            """Read a report and return (repo_id, modifier, is_validated, is_valid)."""
            async with semaphore:
                repo_id, report_path, instance_id = item
                modifier = extract_modifier(instance_id)
                content = await volume_read_text(report_path)
                if content:
                    try:
                        report = json.loads(content)
                        if isinstance(report, dict):
                            p2f = report.get("PASS_TO_FAIL")
                            is_valid = p2f and len(p2f) > 0
                            return (repo_id, modifier, True, is_valid)
                    except json.JSONDecodeError:
                        pass
                return (repo_id, modifier, False, False)

        report_results = await asyncio.gather(
            *[read_report(item) for item in all_report_paths]
        )
        for repo_id, modifier, is_validated, is_valid in report_results:
            if is_validated:
                repo_stats[repo_id]["validated"] += 1
                if is_valid:
                    repo_stats[repo_id]["valid"] += 1

                # Track modifier stats
                if modifier not in modifier_stats:
                    modifier_stats[modifier] = {
                        "generated": 0,
                        "validated": 0,
                        "valid": 0,
                    }
                modifier_stats[modifier]["validated"] += 1
                if is_valid:
                    modifier_stats[modifier]["valid"] += 1

    except Exception as e:
        print(f"Warning: Could not read run_validation directory: {e}")

    # 3. Print formatted output
    import re
    import statistics

    def truncate_repo_name(repo_id: str) -> str:
        """Remove the commit hash suffix (e.g., '.3ec3512d') and replace __ with /."""
        # Pattern matches a dot followed by 8 hex characters at the end
        name = re.sub(r"\.[a-f0-9]{8}$", "", repo_id)
        # Replace __ with / for display
        return name.replace("__", "/")

    def calc_stats(values: list[float]) -> tuple[float, float, float, float, float]:
        """Calculate mean, std, min, median, max for a list of values."""
        if not values:
            return (0, 0, 0, 0, 0)
        mean = statistics.mean(values)
        std = statistics.stdev(values) if len(values) > 1 else 0
        min_val = min(values)
        median = statistics.median(values)
        max_val = max(values)
        return (mean, std, min_val, median, max_val)

    def print_stats_table(
        header: str,
        stats_dict: dict[str, dict[str, int]],
        display_names: dict[str, str] | None = None,
    ) -> None:
        """Print a formatted stats table with totals and statistics."""
        if display_names is None:
            display_names = {k: k for k in stats_dict.keys()}

        max_name_len = (
            max(len(name) for name in display_names.values()) if display_names else 10
        )
        max_name_len = max(max_name_len, len(header))  # At least as wide as header

        total_width = (
            max_name_len + 3 + 6 + 3 + 6 + 3 + 6 + 3 + 8
        )  # name + separators + columns

        print(
            f"{header:<{max_name_len}} | {'Gen':>6} | {'Val':>6} | {'Valid':>6} | {'Pass%':>8}"
        )
        print("-" * total_width)

        total_gen = 0
        total_val = 0
        total_valid = 0

        # Collect per-item values for statistics
        gen_values = []
        val_values = []
        valid_values = []
        pass_rate_values = []

        for item_id, stats in sorted(stats_dict.items()):
            gen = stats["generated"]
            val = stats["validated"]
            valid = stats["valid"]

            total_gen += gen
            total_val += val
            total_valid += valid

            pass_rate = (valid / val * 100) if val > 0 else 0

            gen_values.append(gen)
            val_values.append(val)
            valid_values.append(valid)
            pass_rate_values.append(pass_rate)

            display_name = display_names.get(item_id, item_id)
            print(
                f"{display_name:<{max_name_len}} | {gen:>6} | {val:>6} | {valid:>6} | {pass_rate:>7.1f}%"
            )

        print("-" * total_width)
        total_pass_rate = (total_valid / total_val * 100) if total_val > 0 else 0
        print(
            f"{'TOTAL':<{max_name_len}} | {total_gen:>6} | {total_val:>6} | {total_valid:>6} | {total_pass_rate:>7.1f}%"
        )

        # Calculate and print statistics (mean, std, min, median, max)
        if len(stats_dict) > 0:
            gen_stats = calc_stats(gen_values)
            val_stats = calc_stats(val_values)
            valid_stats = calc_stats(valid_values)
            pass_stats = calc_stats(pass_rate_values)

            print("-" * total_width)
            print(
                f"{'MEAN':<{max_name_len}} | {gen_stats[0]:>6.1f} | {val_stats[0]:>6.1f} | {valid_stats[0]:>6.1f} | {pass_stats[0]:>7.1f}%"
            )
            print(
                f"{'STD':<{max_name_len}} | {gen_stats[1]:>6.1f} | {val_stats[1]:>6.1f} | {valid_stats[1]:>6.1f} | {pass_stats[1]:>7.1f}%"
            )
            print(
                f"{'MIN':<{max_name_len}} | {gen_stats[2]:>6.0f} | {val_stats[2]:>6.0f} | {valid_stats[2]:>6.0f} | {pass_stats[2]:>7.1f}%"
            )
            print(
                f"{'MEDIAN':<{max_name_len}} | {gen_stats[3]:>6.1f} | {val_stats[3]:>6.1f} | {valid_stats[3]:>6.1f} | {pass_stats[3]:>7.1f}%"
            )
            print(
                f"{'MAX':<{max_name_len}} | {gen_stats[4]:>6.0f} | {val_stats[4]:>6.0f} | {valid_stats[4]:>6.0f} | {pass_stats[4]:>7.1f}%"
            )

    # Print Repository table
    display_names = {
        repo_id: truncate_repo_name(repo_id) for repo_id in repo_stats.keys()
    }
    print_stats_table("Repository", repo_stats, display_names)

    # Count repos with >0 valid bugs
    repos_with_valid_bugs = sum(
        1 for stats in repo_stats.values() if stats["valid"] > 0
    )
    print(f"\nNumber of repos with >0 valid bugs: {repos_with_valid_bugs}")
    print(f"Total repos processed: {len(repo_stats)}")

    # Print Modifier table
    if modifier_stats:
        print(f"\n{'=' * 60}\n")
        print_stats_table("Modifier", modifier_stats)

        # Count modifiers with >0 valid bugs
        modifiers_with_valid_bugs = sum(
            1 for stats in modifier_stats.values() if stats["valid"] > 0
        )
        print(f"\nNumber of modifiers with >0 valid bugs: {modifiers_with_valid_bugs}")
        print(f"Total modifiers: {len(modifier_stats)}")


# ============================================================================
# CLI & Main
# ============================================================================


@app.local_entrypoint()
async def main(
    repos: str = "",
    language: str = "javascript",
    max_bugs: int = 200,
    interleave: bool = False,
    max_entities: int = 2000,
    max_candidates: int = 2000,
    max_concurrent_tests: int = 900,
    show_stats: bool = False,
    phases: str = "gen,val,gather,issue",
    issue_gen_config: str = "configs/issue_gen/ig_v2.yaml",
    issue_gen_workers: int = 8,
):
    """
    Modal Bug Generation & Validation script.

    Runs phases specified by --phases (comma-separated):
    - gen: Generation (creates bugs for repos)
    - val: Validation (validates patches from volume)
    - gather: Gather (creates task instances & pushes branches)
    - issue: Issue Generation (generates issue descriptions)

    Run with: modal run scripts/bug_gen.py [OPTIONS]

    Arguments:
        repos: Comma-separated repository names (owner/repo), or empty to use all for language
        language: Language to process (default: javascript)
        max_bugs: Max bugs per modifier (default: 200)
        interleave: Interleave modifiers (default: False)
        max_entities: Max entities to sample, -1 for all (default: 2000)
        max_candidates: Max candidates to process, -1 for all (default: 2000)
        max_concurrent_tests: Max concurrent tests (default: 900)
        show_stats: If True, show bug breakdown stats and exit without running generation/validation
        phases: Comma-separated list of phases to run (default: "gen,val,gather,issue")
        issue_gen_config: Path to issue generation config (default: configs/issue_gen/ig_v2.yaml)
        issue_gen_workers: Number of workers per repo for issue generation (default: 4)
    """
    from swesmith.constants import ENV_NAME

    # Parse repos (comma-separated string to list)
    repo_list = [r.strip() for r in repos.split(",") if r.strip()] if repos else []

    # Handle --show-stats early exit
    if show_stats:
        await show_volume_stats(language, repo_list)
        return

    # Parse and validate phases
    valid_phases = {"gen", "val", "gather", "issue"}
    phase_list = [p.strip() for p in phases.split(",") if p.strip()]
    active_phases = set(phase_list)

    invalid_phases = active_phases - valid_phases
    if invalid_phases:
        print(f"Error: Invalid phases: {invalid_phases}")
        print(f"Valid phases are: {valid_phases}")
        return

    print(f"Running phases: {', '.join(sorted(active_phases))}")

    # Determine repos
    if repo_list:
        target_repos = repo_list
    else:
        target_repos = get_repos_for_language(language)

        print(f"Found {len(target_repos)} repos for '{language}':")
        for r in target_repos:
            print(f"  - {r}")

    if not target_repos:
        print(f"No repos found for language: {language}")
        return

    print(f"\n{'=' * 60}")
    print(f"BUG GEN - {len(target_repos)} repos, {max_concurrent_tests} max concurrent")
    print(f"{'=' * 60}\n")

    # Create a simple args-like object for compatibility
    class Args:
        pass

    args = Args()
    args.max_bugs = max_bugs
    args.interleave = interleave
    args.max_entities = max_entities
    args.max_candidates = max_candidates
    args.timeout_buffer = 60
    args.max_concurrent_tests = max_concurrent_tests

    # Phase 1: Generation (skips repos that are already done/failed)
    generation_results = []
    if "gen" in active_phases:
        generation_results = await run_generation_phase(target_repos, args, language)

    # Phase 2: Validation - collect ALL patches from volume (not just from this run)
    results = []
    if "val" in active_phases:
        print(f"\n{'#' * 60}")
        print("# PHASE 2: VALIDATION")
        print(f"{'#' * 60}\n")

        print("Collecting patches from volume...")
        all_patches = await collect_patches_from_files(target_repos, language)
        print(f"Total: {len(all_patches)} patches\n")

        # For C++, force a longer validation timeout to reduce infra kills.
        validation_timeout_override = 900 if language.lower() == "cpp" else None

        results = await run_validation_phase_async(
            all_patches,
            max_concurrent_tests,
            ENV_NAME,
            validation_timeout_override=validation_timeout_override,
        )

        if results:
            print_summary(results, len(build_repos_with_patches(all_patches)))

    # Report generation errors from this run (if any)
    errors = [r for r in generation_results if "error" in r]
    if errors:
        print(f"\nGeneration Errors ({len(errors)}):")
        for err in errors:
            print(f"  - {err['repo']}: {err.get('error', 'Unknown')}")

    # Phase 3: Gather (Create task instances & Push branches)
    if "gather" in active_phases:
        await run_gather_phase_async(target_repos, language, args)

    # Phase 4: Issue Generation
    if "issue" in active_phases:
        await run_issue_gen_phase_async(
            target_repos,
            language,
            issue_gen_config,
            issue_gen_workers,
        )
