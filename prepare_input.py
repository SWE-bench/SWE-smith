import json
import os
from unidiff import PatchSet

def prepare_input():
    diff_path = "temp_astroid_2496/pr_2496.diff"
    issue_path = "temp_astroid_2496/issue_2492.txt"
    output_path = "pr_2496.jsonl"
    
    # Read diff
    with open(diff_path, 'r') as f:
        patch_set = PatchSet(f)
    
    patch_files = []
    test_patch_files = []
    
    for patched_file in patch_set:
        # Get the raw diff for the file
        file_diff = str(patched_file)
        
        # Determine destination based on path
        # Check both source and target paths, though usually they are similar
        path = patched_file.path
        
        if any(keyword in path.split('/') for keyword in ["test", "tests", "e2e", "testing"]):
            test_patch_files.append(file_diff)
        else:
            patch_files.append(file_diff)
            
    patch_content = "".join(patch_files)
    test_patch_content = "".join(test_patch_files)
    
    print(f"Patch length: {len(patch_content)}")
    print(f"Test patch length: {len(test_patch_content)}")
    
    # Create input object
    entry = {
        "repo": "pylint-dev/astroid",
        "pull_number": 2496,
        "instance_id": "pylint-dev__astroid-2496",
        "patch": patch_content,
        "test_patch": test_patch_content,
        "base_commit": "b114f6b5", # From plan
    }
    
    # Write JSONL
    with open(output_path, 'w') as f:
        f.write(json.dumps(entry) + "\n")
    
    print(f"Created {output_path}")

if __name__ == "__main__":
    prepare_input()

