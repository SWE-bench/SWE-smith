#!/usr/bin/env python3
"""
Purpose: Automated APEX task creation from repositories

This script automates the entire pipeline:
1. Install repositories
2. Create Docker images
3. Generate bugs (procedural or LLM-based)
4. Collect patches
5. Validate bugs
6. Export to APEX tasks

Usage: python scripts/create_apex_tasks.py repos.txt --strategy procedural --max-bugs 10
"""

import argparse
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import List, Optional, Tuple


class APEXTaskCreator:
    """Handles the complete APEX task creation pipeline."""
    
    def __init__(self, strategy: str = "procedural", max_bugs: int = 10, 
                 llm_model: str = "openai/gpt-4o", log_file: str = "apex_creation.log"):
        self.strategy = strategy
        self.max_bugs = max_bugs
        self.llm_model = llm_model
        self.log_file = log_file
        
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger(__name__)
    
    def parse_repos_file(self, repos_file: str) -> List[Tuple[str, str]]:
        """Parse the repos.txt file and return list of (repo_name, commit_hash) tuples."""
        repos = []
        
        try:
            with open(repos_file, 'r') as f:
                for line_num, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith('#'):
                        continue
                    
                    # Expected format: owner/repo_name,commit_hash
                    # Example: Instagram/MonkeyType,70c3acf62950be5dfb28743c7a719bfdecebcd84
                    parts = line.split(',')
                    if len(parts) != 2:
                        self.logger.warning(f"Skipping invalid line {line_num}: {line}")
                        continue
                    
                    repo_name = parts[0].strip()
                    commit_hash = parts[1].strip()
                    
                    if not repo_name or not commit_hash:
                        self.logger.warning(f"Skipping empty fields in line {line_num}: {line}")
                        continue
                    
                    repos.append((repo_name, commit_hash))
                    
        except FileNotFoundError:
            self.logger.error(f"Repository file not found: {repos_file}")
            sys.exit(1)
        except Exception as e:
            self.logger.error(f"Error reading repository file: {e}")
            sys.exit(1)
        
        self.logger.info(f"Parsed {len(repos)} repositories from {repos_file}")
        return repos
    
    def generate_profile_name(self, repo_name: str, commit_hash: str) -> str:
        """Generate the profile name for Docker image creation."""
        # Convert Instagram/MonkeyType to instagram_1776_monkeytype
        owner, repo = repo_name.split('/')
        profile_name = f"{owner.lower()}_1776_{repo.lower()}.{commit_hash[:8]}"
        return f"jyangballin/swesmith.x86_64.{profile_name}"
    
    def generate_repo_id(self, repo_name: str, commit_hash: str) -> str:
        """Generate the repository ID used in swesmith."""
        # Convert Instagram/MonkeyType to Instagram__MonkeyType.70c3acf6
        owner, repo = repo_name.split('/')
        return f"{owner}__{repo}.{commit_hash[:8]}"
    
    def run_command(self, cmd: List[str], step_name: str) -> bool:
        """Run a command and return True if successful, False otherwise."""
        self.logger.info(f"[{step_name}] Running: {' '.join(cmd)}")
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode == 0:
                self.logger.info(f"[{step_name}] ✓ Success")
                if result.stdout:
                    self.logger.debug(f"[{step_name}] STDOUT: {result.stdout}")
                return True
            else:
                self.logger.error(f"[{step_name}] ✗ Failed with return code {result.returncode}")
                if result.stdout:
                    self.logger.error(f"[{step_name}] STDOUT: {result.stdout}")
                if result.stderr:
                    self.logger.error(f"[{step_name}] STDERR: {result.stderr}")
                return False
                
        except subprocess.TimeoutExpired:
            self.logger.error(f"[{step_name}] ✗ Command timed out")
            return False
        except Exception as e:
            self.logger.error(f"[{step_name}] ✗ Exception: {e}")
            return False
    
    def step_install_repo(self, repo_name: str, commit_hash: str) -> bool:
        """Step 1: Install repository."""
        cmd = [
            "python", "-m", "swesmith.build_repo.try_install_py",
            repo_name,
            "configs/install_repo.sh",
            "--commit", commit_hash
        ]
        return self.run_command(cmd, "INSTALL_REPO")
    
    def step_create_images(self, profile_name: str) -> bool:
        """Step 2: Create Docker images."""
        cmd = [
            "python", "-m", "swesmith.build_repo.create_images",
            "--profiles", profile_name
        ]
        return self.run_command(cmd, "CREATE_IMAGES")
    
    def step_generate_bugs(self, repo_id: str) -> bool:
        """Step 3: Generate bugs (procedural or LLM-based)."""
        if self.strategy == "procedural":
            cmd = [
                "python", "-m", "swesmith.bug_gen.procedural.generate",
                repo_id,
                "--max_bugs", str(self.max_bugs)
            ]
        elif self.strategy == "llm":
            cmd = [
                "python", "-m", "swesmith.bug_gen.llm.modify",
                repo_id,
                "--n_bugs", "1",
                "--max_bugs", str(self.max_bugs),
                "--model", self.llm_model,
                "--config_file", "configs/bug_gen/lm_modify.yml"
            ]
        else:
            self.logger.error(f"Unknown strategy: {self.strategy}")
            return False
        
        return self.run_command(cmd, "GENERATE_BUGS")
    
    def step_collect_patches(self, repo_id: str) -> bool:
        """Step 4: Collect patches."""
        cmd = [
            "python", "-m", "swesmith.bug_gen.collect_patches",
            f"logs/bug_gen/{repo_id}"
        ]
        return self.run_command(cmd, "COLLECT_PATCHES")
    
    def step_validate_bugs(self, repo_id: str) -> bool:
        """Step 5: Validate bugs."""
        cmd = [
            "python", "-m", "swesmith.harness.valid",
            f"logs/bug_gen/{repo_id}_all_patches.json"
        ]
        return self.run_command(cmd, "VALIDATE_BUGS")
    
    def step_export_apex_tasks(self, repo_id: str) -> bool:
        """Step 6: Export to APEX tasks."""
        cmd = [
            "python", "-m", "swesmith.apex_exporter",
            "--filter-repo", repo_id.split('.')[0],  # Instagram__MonkeyType
            "--max-tasks", "100",
            "--output-dir", "tasks"
        ]
        return self.run_command(cmd, "EXPORT_APEX_TASKS")
    
    def process_repository(self, repo_name: str, commit_hash: str) -> bool:
        """Process a single repository through the entire pipeline."""
        repo_id = self.generate_repo_id(repo_name, commit_hash)
        profile_name = self.generate_profile_name(repo_name, commit_hash)
        
        self.logger.info(f"=== Processing {repo_name} @ {commit_hash[:8]} ===")
        self.logger.info(f"Repository ID: {repo_id}")
        self.logger.info(f"Profile Name: {profile_name}")
        
        # Step 1: Install repository
        if not self.step_install_repo(repo_name, commit_hash):
            self.logger.error(f"Failed to install {repo_name}, skipping...")
            return False
        
        # Step 2: Create Docker images
        if not self.step_create_images(profile_name):
            self.logger.error(f"Failed to create images for {repo_name}, skipping...")
            return False
        
        # Step 3: Generate bugs
        if not self.step_generate_bugs(repo_id):
            self.logger.error(f"Failed to generate bugs for {repo_name}, skipping...")
            return False
        
        # Step 4: Collect patches
        if not self.step_collect_patches(repo_id):
            self.logger.error(f"Failed to collect patches for {repo_name}, skipping...")
            return False
        
        # Step 5: Validate bugs
        if not self.step_validate_bugs(repo_id):
            self.logger.error(f"Failed to validate bugs for {repo_name}, skipping...")
            return False
        
        # Step 6: Export APEX tasks
        if not self.step_export_apex_tasks(repo_id):
            self.logger.error(f"Failed to export APEX tasks for {repo_name}, skipping...")
            return False
        
        self.logger.info(f"✓ Successfully processed {repo_name}")
        return True
    
    def run(self, repos_file: str):
        """Run the complete pipeline for all repositories."""
        start_time = time.time()
        
        self.logger.info("=== APEX Task Creation Pipeline Started ===")
        self.logger.info(f"Strategy: {self.strategy}")
        self.logger.info(f"Max bugs: {self.max_bugs}")
        if self.strategy == "llm":
            self.logger.info(f"LLM Model: {self.llm_model}")
        
        # Parse repositories
        repos = self.parse_repos_file(repos_file)
        
        # Process each repository
        successful_repos = []
        failed_repos = []
        
        for repo_name, commit_hash in repos:
            try:
                if self.process_repository(repo_name, commit_hash):
                    successful_repos.append(repo_name)
                else:
                    failed_repos.append(repo_name)
            except Exception as e:
                self.logger.error(f"Unexpected error processing {repo_name}: {e}")
                failed_repos.append(repo_name)
            
            # Add separator between repositories
            self.logger.info("")
        
        # Summary
        end_time = time.time()
        duration = end_time - start_time
        
        self.logger.info("=== APEX Task Creation Pipeline Completed ===")
        self.logger.info(f"Total repositories: {len(repos)}")
        self.logger.info(f"Successful: {len(successful_repos)}")
        self.logger.info(f"Failed: {len(failed_repos)}")
        self.logger.info(f"Duration: {duration:.2f} seconds")
        
        if successful_repos:
            self.logger.info(f"✓ Successful repositories: {', '.join(successful_repos)}")
        
        if failed_repos:
            self.logger.info(f"✗ Failed repositories: {', '.join(failed_repos)}")


def main():
    parser = argparse.ArgumentParser(
        description="Automated APEX task creation from repositories"
    )
    parser.add_argument(
        "repos_file",
        help="Path to repos.txt file containing repository names and commit hashes"
    )
    parser.add_argument(
        "--strategy",
        choices=["procedural", "llm"],
        default="procedural",
        help="Bug generation strategy (default: procedural)"
    )
    parser.add_argument(
        "--max-bugs",
        type=int,
        default=10,
        help="Maximum number of bugs to generate (default: 10)"
    )
    parser.add_argument(
        "--llm-model",
        default="openai/gpt-4o",
        help="LLM model to use for bug generation (default: openai/gpt-4o)"
    )
    parser.add_argument(
        "--log-file",
        default="apex_creation.log",
        help="Log file path (default: apex_creation.log)"
    )
    
    args = parser.parse_args()
    
    # Create APEX task creator
    creator = APEXTaskCreator(
        strategy=args.strategy,
        max_bugs=args.max_bugs,
        llm_model=args.llm_model,
        log_file=args.log_file
    )
    
    # Run the pipeline
    creator.run(args.repos_file)


if __name__ == "__main__":
    main() 