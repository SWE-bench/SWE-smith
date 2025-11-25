#!/usr/bin/env python3
"""
End-to-End Bug Generation Pipeline

This script orchestrates the complete workflow:
1. Generate repository profile using mini-swe-agent
2. Add profile to appropriate profiles file
3. Generate procedural bugs
4. Run validation (local or Modal)
5. Analyze generated bugs

Usage:
    python scripts/end_to_end_bug_gen.py <repo_name> --language <lang> [options]

Examples:
    # Local validation
    python scripts/end_to_end_bug_gen.py google/gson --language java --max-bugs 50 --livestream --verify
    
    # Modal validation (massively parallel)
    python scripts/end_to_end_bug_gen.py google/gson --language java --max-bugs 100 --use-modal
"""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Optional, Tuple


def run_command(cmd: list, description: str, capture_output: bool = False, tee_output: Optional[Path] = None) -> Tuple[int, str]:
    """Run a command and optionally capture output."""
    print(f"\n{'='*80}")
    print(f"🚀 {description}")
    print(f"{'='*80}")
    print(f"Command: {' '.join(cmd)}")
    print()

    if tee_output:
        # Use subprocess.Popen to stream output while saving to file
        with open(tee_output, 'w') as f:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                universal_newlines=True
            )
            
            output_lines = []
            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    print(line.rstrip())
                    f.write(line)
                    output_lines.append(line)
            
            returncode = process.wait()
            full_output = ''.join(output_lines)
    elif capture_output:
        result = subprocess.run(cmd, capture_output=True, text=True)
        full_output = result.stdout + result.stderr
        print(full_output)
        returncode = result.returncode
    else:
        result = subprocess.run(cmd)
        returncode = result.returncode
        full_output = ""

    if returncode == 0:
        print(f"\n✅ {description} completed successfully")
    else:
        print(f"\n❌ {description} failed with exit code {returncode}")
    
    return returncode, full_output


def extract_repo_info(repo_name: str) -> Tuple[str, str]:
    """Extract owner and repo from repo_name."""
    if '/' not in repo_name:
        raise ValueError("Repository name must be in format 'owner/repo'")
    
    parts = repo_name.split('/')
    if len(parts) != 2:
        raise ValueError("Repository name must be in format 'owner/repo'")
    
    return parts[0], parts[1]


def get_profile_file_for_language(language: str) -> str:
    """Get the profile file path for a given language."""
    language = language.lower()
    
    language_files = {
        'python': 'swesmith/profiles/python.py',
        'javascript': 'swesmith/profiles/javascript.py',
        'go': 'swesmith/profiles/golang.py',
        'golang': 'swesmith/profiles/golang.py',
        'rust': 'swesmith/profiles/rust.py',
        'java': 'swesmith/profiles/java.py',
        'c': 'swesmith/profiles/c.py',
        'cpp': 'swesmith/profiles/cpp.py',
        'c++': 'swesmith/profiles/cpp.py',
        'csharp': 'swesmith/profiles/csharp.py',
        'c#': 'swesmith/profiles/csharp.py',
        'php': 'swesmith/profiles/php.py',
    }
    
    return language_files.get(language, 'swesmith/profiles/base.py')


def load_generated_profile(repo_name: str) -> Optional[Tuple[str, dict]]:
    """Load the generated profile from agent results."""
    owner, repo = extract_repo_info(repo_name)
    result_dir = Path("agent-result") / f"{owner}-{repo}"
    
    profile_file = result_dir / "generated_profiles" / "profile_class.py"
    metadata_file = result_dir / "generated_profiles" / "profile_metadata.json"
    
    if not profile_file.exists():
        print(f"❌ Profile file not found: {profile_file}")
        return None
    
    if not metadata_file.exists():
        print(f"❌ Metadata file not found: {metadata_file}")
        return None
    
    with open(profile_file, 'r', encoding='utf-8') as f:
        profile_code = f.read()
    
    with open(metadata_file, 'r', encoding='utf-8') as f:
        metadata = json.load(f)
    
    print(f"✅ Loaded generated profile for {repo_name}")
    print(f"   Class name: {metadata['profile_class_name']}")
    print(f"   Language: {metadata['language']}")
    print(f"   Integration ready: {metadata['integration_ready']}")
    
    return profile_code, metadata


def insert_profile_into_file(profile_code: str, target_file: str, class_name: str, org_gh: str = None, org_dh: str = None) -> bool:
    """Insert the generated profile into the target profiles file."""
    target_path = Path(target_file)
    
    if not target_path.exists():
        print(f"❌ Target profile file not found: {target_file}")
        return False
    
    # Add org_gh and org_dh to the profile code if provided
    if org_gh or org_dh:
        # Find the commit line and insert org fields after it
        lines = profile_code.split('\n')
        new_lines = []
        for i, line in enumerate(lines):
            new_lines.append(line)
            # Insert after the commit field
            if 'commit: str = ' in line and 'commit: str = "' in line:
                indent = len(line) - len(line.lstrip())
                if org_gh:
                    new_lines.append(' ' * indent + f'org_gh: str = "{org_gh}"  # Custom GitHub org for mirror')
                if org_dh:
                    new_lines.append(' ' * indent + f'org_dh: str = "{org_dh}"  # Custom Docker Hub org')
        profile_code = '\n'.join(new_lines)
    
    # Read the existing file
    with open(target_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Check if this profile already exists
    if f"class {class_name}" in content:
        print(f"⚠️  Profile {class_name} already exists in {target_file}")
        response = input("Overwrite? (y/n): ").strip().lower()
        if response != 'y':
            print("Skipping profile insertion")
            return False
        
        # Remove the old profile (simple approach: find the class and remove until next class or registration)
        pattern = rf"@dataclass\nclass {class_name}.*?(?=@dataclass\nclass |\n# Register all |$)"
        content = re.sub(pattern, "", content, flags=re.DOTALL)
    
    # Find the registration loop at the end
    registration_pattern = r"# Register all .*? profiles? with the global registry.*?registry\.register_profile\(obj\)"
    registration_match = re.search(registration_pattern, content, re.DOTALL)
    
    if registration_match:
        # Insert before the registration loop
        insert_pos = registration_match.start()
        new_content = content[:insert_pos] + profile_code + "\n" + content[insert_pos:]
    else:
        # Just append at the end
        new_content = content + "\n\n" + profile_code
    
    # Write back
    with open(target_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"✅ Profile {class_name} added to {target_file}")
    return True


def get_repo_id_from_profile(profile_code: str, metadata: dict) -> Optional[str]:
    """Extract the repo_id that will be used by SWE-smith."""
    # The repo_id format is: owner__repo.commit[:8]
    owner = metadata.get('repository', '').split('/')[0]
    repo = metadata.get('repository', '').split('/')[1] if '/' in metadata.get('repository', '') else ''
    commit = metadata.get('commit', 'unknown')[:8]
    
    if owner and repo and commit != 'unknown':
        return f"{owner}__{repo}.{commit}"
    
    # Try to extract from class name
    class_name = metadata.get('profile_class_name', '')
    if class_name:
        # Class names are like: Gson50a93686
        # We need to get the profile and query it
        return None  # Will be determined dynamically
    
    return None


def get_repo_id_from_registry(repo_name: str) -> Optional[str]:
    """Get the repo_id from the profile registry."""
    owner, repo = extract_repo_info(repo_name)
    
    # Run a Python snippet to query the registry
    python_code = f"""
from swesmith.profiles import registry
import sys

target = '{owner}/{repo}'

# Try to find a profile matching owner/repo
for key in registry.keys():
    try:
        profile = registry.get(key)
        if f'{{profile.owner}}/{{profile.repo}}' == target:
            print(key)
            sys.exit(0)
    except Exception:
        continue

sys.exit(1)
"""
    
    result = subprocess.run([sys.executable, '-c', python_code], capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout.strip()
    
    return None


def get_org_gh_from_profile(repo_id: str) -> Optional[str]:
    """Get the org_gh from the profile registry."""
    python_code = f"""
from swesmith.profiles import registry
import sys

try:
    profile = registry.get('{repo_id}')
    if hasattr(profile, 'org_gh'):
        print(profile.org_gh)
        sys.exit(0)
except Exception:
    pass

sys.exit(1)
"""
    
    result = subprocess.run([sys.executable, '-c', python_code], capture_output=True, text=True)
    
    if result.returncode == 0:
        return result.stdout.strip()
    
    return None


def build_docker_image(repo_id: str) -> bool:
    """Build Docker image for the repository.
    
    Note: generate_profile.py cleans up images after Stage 2, so we need to rebuild.
    
    Args:
        repo_id: Repository ID (e.g., google__gson.dd2fe59c)
    
    Returns:
        True if build successful, False if failed
    """
    try:
        from swesmith.profiles import registry
        profile = registry.get(repo_id)
        image_name = profile.image_name
        
        print(f"\n🏗️  Building Docker image for Modal...")
        print(f"   Image: {image_name}")
        print(f"   (Note: generate_profile.py cleans up after Stage 2, so we rebuild for Modal)")
        
        # Check if image already exists
        check_result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            check=False
        )
        
        if check_result.returncode == 0:
            print(f"✅ Docker image already exists locally")
            return True
        
        # Build from the profile's Dockerfile property
        from swesmith.profiles import registry
        profile = registry.get(repo_id)
        
        # Create temporary build directory
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            dockerfile_path = Path(tmpdir) / "Dockerfile"
            
            # Write the profile's Dockerfile
            print(f"   Using Dockerfile from profile registry")
            with open(dockerfile_path, 'w') as f:
                f.write(profile.dockerfile)
            
            # Build the image
            build_cmd = [
                "docker",
                "build",
                "--no-cache",  # Force rebuild to avoid stale cached layers
                "-f", str(dockerfile_path),
                "-t", image_name,
                tmpdir  # Build context
            ]
            
            print(f"   Building: {' '.join(build_cmd)}")
            build_result = subprocess.run(
                build_cmd,
                capture_output=False,  # Show build progress
                check=False
            )
        
        # Check if build was successful by verifying the image exists
        verify_result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            check=False
        )
        
        if verify_result.returncode == 0:
            print(f"✅ Successfully built Docker image")
            return True
        else:
            print(f"❌ Failed to build Docker image")
            print(f"   The build command may have failed internally")
            print(f"   Check the output above for errors (e.g., missing GITHUB_TOKEN)")
            return False
            
    except Exception as e:
        print(f"❌ Error building Docker image: {e}")
        return False


def push_docker_image(repo_id: str) -> bool:
    """Push Docker image to Docker Hub after building.
    
    Args:
        repo_id: Repository ID (e.g., google__gson.dd2fe59c)
    
    Returns:
        True if push successful or not needed, False if failed
    """
    try:
        from swesmith.profiles import registry
        profile = registry.get(repo_id)
        image_name = profile.image_name
        
        print(f"\n🐳 Pushing Docker image to Docker Hub...")
        print(f"   Image: {image_name}")
        
        # Check if image exists locally first
        check_result = subprocess.run(
            ["docker", "image", "inspect", image_name],
            capture_output=True,
            check=False
        )
        
        if check_result.returncode != 0:
            print(f"⚠️  Warning: Docker image {image_name} not found locally")
            print("   Skipping push - image will need to be built first")
            return False
        
        # Push the image
        push_result = subprocess.run(
            ["docker", "push", image_name],
            capture_output=False,  # Show progress
            check=False
        )
        
        if push_result.returncode == 0:
            print(f"✅ Successfully pushed Docker image to Docker Hub")
            return True
        else:
            print(f"❌ Failed to push Docker image (exit code: {push_result.returncode})")
            print("   Make sure you're logged in to Docker Hub: docker login")
            print("   Make sure you have permission to push to this repository")
            return False
            
    except Exception as e:
        print(f"❌ Error pushing Docker image: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="End-to-end bug generation pipeline: profile → bugs → analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline with verification and livestream
  python scripts/end_to_end_bug_gen.py google/gson --language java --max-bugs 50 --livestream --verify
  
  # Quick pipeline without verification
  python scripts/end_to_end_bug_gen.py fastapi/typer --language python --max-bugs 20
  
  # Use Modal for massively parallel validation (requires Modal setup)
  python scripts/end_to_end_bug_gen.py google/gson --language java --max-bugs 100 --use-modal
  
  # Custom model and organizations
  python scripts/end_to_end_bug_gen.py rust-lang/cargo --language rust --model gpt-4o-mini --max-bugs 30 \
      --org-gh my-org --org-dh my-dockerhub
        """
    )
    
    # Required arguments
    parser.add_argument(
        'repo_name',
        help='GitHub repository in format "owner/repo" (e.g., google/gson)'
    )
    parser.add_argument(
        '--language',
        required=True,
        help='Programming language of the repository (python, java, javascript, go, rust, etc.)'
    )
    
    # Profile generation options (forwarded to generate_profile.py)
    parser.add_argument(
        '--model',
        default='claude-sonnet-4-20250514',
        help='Model to use for profile generation (default: claude-sonnet-4-20250514)'
    )
    parser.add_argument(
        '--livestream',
        action='store_true',
        help='Enable livestream output during profile generation'
    )
    parser.add_argument(
        '--verify',
        action='store_true',
        help='Verify the generated Dockerfile by building it'
    )
    parser.add_argument(
        '--max-cost',
        type=float,
        default=2.0,
        help='Maximum cost in dollars for profile generation (default: 2.0)'
    )
    parser.add_argument(
        '--max-time',
        type=int,
        default=1200,
        help='Maximum time in seconds for profile generation (default: 1200)'
    )
    
    # Bug generation options
    parser.add_argument(
        '--max-bugs',
        type=int,
        default=5,
        help='Maximum bugs per modifier (default: 5)'
    )
    parser.add_argument(
        '--use-modal',
        action='store_true',
        help='Use Modal for massively parallel validation (requires Modal setup)'
    )
    parser.add_argument(
        '--validation-timeout',
        type=int,
        default=600,
        help='Timeout in seconds for validation step (default: 600)'
    )
    
    # Organization options (for profile generation)
    parser.add_argument(
        '--org-gh',
        default='cs329a-swesmith-repos',
        help='GitHub organization for repository mirrors (default: cs329a-swesmith-repos)'
    )
    parser.add_argument(
        '--org-dh',
        default='priyank0003',
        help='Docker Hub organization for images (default: priyank0003)'
    )
    
    # Pipeline control
    parser.add_argument(
        '--skip-profile-gen',
        action='store_true',
        help='Skip profile generation (profile already exists in registry)'
    )
    parser.add_argument(
        '--skip-agent',
        action='store_true',
        help='Skip agent run but regenerate profile from existing agent-result directory'
    )
    parser.add_argument(
        '--skip-bug-gen',
        action='store_true',
        help='Skip bug generation'
    )
    parser.add_argument(
        '--skip-analysis',
        action='store_true',
        help='Skip bug analysis'
    )
    parser.add_argument(
        '--force-docker-push',
        action='store_true',
        help='Force Docker image build and push (useful for testing Docker workflow without re-running profile gen)'
    )
    
    args = parser.parse_args()
    
    try:
        owner, repo = extract_repo_info(args.repo_name)
        print(f"\n🎯 End-to-End Bug Generation Pipeline")
        print(f"   Repository: {args.repo_name}")
        print(f"   Language: {args.language}")
        print(f"   Max bugs: {args.max_bugs}")
        print()
        
        # Step 1: Generate profile (unless skipped)
        if not args.skip_profile_gen:
            print("\n" + "="*80)
            print("STEP 1: PROFILE GENERATION")
            print("="*80)
            
            output_log = Path(f"{owner}-{repo}-gen.out")
            
            # Check if we should skip agent run but regenerate profile
            if args.skip_agent:
                print("\n⏭️  Skipping agent run (--skip-agent)")
                print("   Reusing existing agent-result directory")
                
                # Check if agent-result directory exists
                agent_result_dir = Path(f"agent-result/{owner}-{repo}")
                if not agent_result_dir.exists():
                    print(f"\n❌ Agent result directory not found: {agent_result_dir}")
                    print("   Cannot skip agent run without existing agent results")
                    sys.exit(1)
                
                print(f"✅ Found existing agent-result directory: {agent_result_dir}")
            else:
                # Build command for generate_profile.py
                gen_cmd = [
                    sys.executable,
                    "mini-swe-agent-automate-repo-installation/generate_profile.py",
                    args.repo_name,
                    "--model", args.model,
                    "--max-cost", str(args.max_cost),
                    "--max-time", str(args.max_time),
                ]
                
                if args.language.lower() == 'python':
                    gen_cmd.append('--python-repo')
                
                if args.livestream:
                    gen_cmd.append('--livestream')
                
                if args.verify:
                    gen_cmd.append('--verify')
                
                exit_code, _ = run_command(gen_cmd, "Generating profile", tee_output=output_log)
                
                if exit_code != 0:
                    print(f"\n❌ Profile generation failed. Check {output_log} for details.")
                    sys.exit(1)
            
            # Load and insert the generated profile
            result = load_generated_profile(args.repo_name)
            if not result:
                print("\n❌ Failed to load generated profile")
                sys.exit(1)
            
            profile_code, metadata = result
            
            # Determine target file
            target_file = get_profile_file_for_language(args.language)
            print(f"\n📝 Target profile file: {target_file}")
            
            # Insert the profile
            if not insert_profile_into_file(profile_code, target_file, metadata['profile_class_name'], 
                                           org_gh=args.org_gh, org_dh=args.org_dh):
                print("\n❌ Failed to insert profile into target file")
                sys.exit(1)
            
            print(f"\n✅ Profile successfully added to {target_file}")
            
            # Reload the profiles module to pick up the new profile
            print("🔄 Reloading profiles module to register new profile...")
            import importlib
            import swesmith.profiles
            # Get the specific language profile module
            profile_module_name = f"swesmith.profiles.{args.language.lower()}"
            if args.language.lower() in ['go', 'golang']:
                profile_module_name = "swesmith.profiles.golang"
            elif args.language.lower() in ['c++', 'cpp']:
                profile_module_name = "swesmith.profiles.cpp"
            elif args.language.lower() in ['c#', 'csharp']:
                profile_module_name = "swesmith.profiles.csharp"
            
            try:
                # Reload the specific profile module
                if profile_module_name in sys.modules:
                    importlib.reload(sys.modules[profile_module_name])
                else:
                    __import__(profile_module_name)
                print("✅ Profiles module reloaded successfully")
            except Exception as e:
                print(f"⚠️  Warning: Could not reload profiles module: {e}")
                print("   This is okay - profile will be registered on next import")
        else:
            print("\n⏭️  Skipping profile generation (--skip-profile-gen)")
        
        # Get repo_id from registry
        repo_id = get_repo_id_from_registry(args.repo_name)
        if not repo_id:
            print(f"\n❌ Failed to find repo_id for {args.repo_name} in profile registry")
            print("   Make sure the profile was added successfully and the registry is updated")
            sys.exit(1)
        
        print(f"\n✅ Found repo_id in registry: {repo_id}")
        
        # Build and push Docker image to Docker Hub if using Modal validation
        # (Modal needs to pull the image from a registry)
        # Note: generate_profile.py cleans up the image after Stage 2, so we rebuild
        if (args.use_modal and not args.skip_profile_gen) or args.force_docker_push:
            if args.force_docker_push and args.skip_profile_gen:
                print("\n" + "="*80)
                print("DOCKER BUILD & PUSH (--force-docker-push)")
                print("="*80)
            
            # First, rebuild the image (it was cleaned up by generate_profile.py)
            build_success = build_docker_image(repo_id)
            if not build_success:
                print("\n❌ Failed to build Docker image")
                print("   Modal validation requires a Docker image")
                sys.exit(1)
            
            # Then, push it to Docker Hub
            push_success = push_docker_image(repo_id)
            if not push_success:
                print("\n⚠️  Warning: Failed to push Docker image to Docker Hub")
                print("   Modal validation requires the image to be available on Docker Hub")
                print("   You can:")
                print("   1. Login to Docker Hub: docker login")
                print("   2. Manually push the image later")
                print("   3. Continue with local validation (remove --use-modal flag)")
                
                # Ask user if they want to continue
                response = input("\n❓ Continue anyway? (y/N): ").strip().lower()
                if response not in ['y', 'yes']:
                    print("Exiting...")
                    sys.exit(1)
        
        # Step 2: Generate bugs (unless skipped)
        if not args.skip_bug_gen:
            print("\n" + "="*80)
            print("STEP 2: PROCEDURAL BUG GENERATION")
            print("="*80)
            
            # Step 2a: Generate bugs procedurally
            print("\n[Step 2a/3] Generating bugs procedurally...")
            bug_gen_cmd = [
                sys.executable,
                "-m",
                "swesmith.bug_gen.procedural.generate",
                repo_id,
                "--max_bugs",
                str(args.max_bugs)
            ]
            
            exit_code, _ = run_command(bug_gen_cmd, "Generating procedural bugs")
            
            if exit_code != 0:
                print(f"\n⚠️  Bug generation had errors, but may have partial results")
                response = input("Continue to patch collection? (y/n): ").strip().lower()
                if response != 'y':
                    sys.exit(1)
            
            # Step 2b: Collect all patches
            print("\n[Step 2b/3] Collecting all patches...")
            patches_file = f"logs/bug_gen/{repo_id}_all_patches.json"
            
            collect_cmd = [
                sys.executable,
                "-m",
                "swesmith.bug_gen.collect_patches",
                f"logs/bug_gen/{repo_id}"
            ]
            
            exit_code, _ = run_command(collect_cmd, "Collecting patches")
            
            if exit_code != 0:
                print(f"\n❌ Patch collection failed")
                sys.exit(1)
            
            # Verify patches file was created
            if Path(patches_file).exists():
                with open(patches_file, 'r') as f:
                    patches = json.load(f)
                    num_patches = len(patches)
                print(f"✅ Collected {num_patches} patches to {patches_file}")
            else:
                print(f"❌ Patches file not found: {patches_file}")
                sys.exit(1)
            
            # Step 2c: Run validation
            print("\n[Step 2c/3] Running validation...")
            
            if args.use_modal:
                print(f"Using Modal for massively parallel validation...")
                validate_cmd = [
                    "modal",
                    "run",
                    "-m",
                    "swesmith.harness.valid_modal",
                    "--bug-patches",
                    patches_file
                ]
            else:
                # Determine number of workers
                import multiprocessing
                num_workers = multiprocessing.cpu_count()
                print(f"Using local validation with {num_workers} workers...")
                
                validate_cmd = [
                    sys.executable,
                    "-m",
                    "swesmith.harness.valid",
                    patches_file,
                    "-w",
                    str(num_workers)
                ]
            
            try:
                exit_code, _ = run_command(validate_cmd, "Running validation")
                
                if exit_code != 0:
                    print(f"\n⚠️  Validation had errors, but may have partial results")
            except subprocess.TimeoutExpired:
                print(f"\n⚠️  Validation timed out after {args.validation_timeout} seconds")
                print("Partial results may be available")
            
        else:
            print("\n⏭️  Skipping bug generation (--skip-bug-gen)")
        
        # Step 3: Analyze bugs (unless skipped)
        if not args.skip_analysis:
            print("\n" + "="*80)
            print("STEP 3: BUG ANALYSIS")
            print("="*80)
            
            print(f"📂 Analysis path: logs/bug_gen/{repo_id}")
            
            analysis_cmd = [
                sys.executable,
                "scripts/analyze_bugs.py",
                repo_id
            ]
            
            exit_code, _ = run_command(analysis_cmd, "Analyzing generated bugs", capture_output=True)
            
            if exit_code != 0:
                print(f"\n⚠️  Bug analysis had errors")
        else:
            print("\n⏭️  Skipping bug analysis (--skip-analysis)")
        
        # Final summary
        print("\n" + "="*80)
        print("🎉 PIPELINE COMPLETE")
        print("="*80)
        print(f"\nRepository: {args.repo_name}")
        print(f"Repo ID: {repo_id}")
        if not args.skip_profile_gen:
            print(f"GitHub Org: {args.org_gh}")
            print(f"Docker Hub Org: {args.org_dh}")
        if not args.skip_bug_gen:
            print(f"Validation: {'Modal (parallel)' if args.use_modal else 'Local'}")
        
        print(f"\nGenerated artifacts:")
        print(f"  - Profile: {get_profile_file_for_language(args.language)}")
        print(f"  - Bugs: logs/bug_gen/{repo_id}/")
        print(f"  - Patches: logs/bug_gen/{repo_id}_all_patches.json")
        print(f"  - Validation: logs/run_validation/{repo_id}/")
        print(f"  - Analysis: logs/analysis/{repo_id}_analysis.json")
        print("\n" + "="*80)
        
    except KeyboardInterrupt:
        print("\n\n⏹️  Pipeline interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

