import urllib.request
import json
import sys
import os
import ssl

def download_file(url, path):
    print(f"Downloading {url} to {path}...")
    try:
        # Create an unverified context to avoid SSL errors in some envs
        context = ssl._create_unverified_context()
        with urllib.request.urlopen(url, context=context) as response, open(path, 'wb') as out_file:
            out_file.write(response.read())
        print("Download successful.")
    except Exception as e:
        print(f"Error downloading: {e}")

def fetch_issue(owner, repo, issue_number):
    url = f"https://api.github.com/repos/{owner}/{repo}/issues/{issue_number}"
    print(f"Fetching issue from {url}...")
    try:
        context = ssl._create_unverified_context()
        req = urllib.request.Request(url, headers={'User-Agent': 'Python-urllib'})
        with urllib.request.urlopen(req, context=context) as response:
            data = json.loads(response.read().decode())
            print("Issue Title:", data.get('title'))
            body = data.get('body', '')
            with open(f"temp_astroid_2496/issue_{issue_number}.txt", 'w') as f:
                f.write(body)
            print("Issue fetched successfully.")
    except Exception as e:
        print(f"Error fetching issue: {e}")

def check_package(package_name):
    try:
        __import__(package_name)
        print(f"Package '{package_name}' is installed.")
    except ImportError:
        print(f"Package '{package_name}' is NOT installed.")

if __name__ == "__main__":
    os.makedirs("temp_astroid_2496", exist_ok=True)
    
    # Download diff
    download_file("https://github.com/pylint-dev/astroid/pull/2496.diff", "temp_astroid_2496/pr_2496.diff")
    
    # Fetch Issue
    fetch_issue("pylint-dev", "astroid", 2492)
    
    # Check unidiff
    check_package("unidiff")
