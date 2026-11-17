"""
Direct GitHub Uploader Script for Bank Fraud Detection Engine.
Uploads the codebase directly to your GitHub account using the GitHub REST API.
Does not require git.exe to be installed.
"""

import os
import sys
import base64
import argparse
import requests

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))

IGNORE_PATTERNS = {
    ".git", "__pycache__", ".pytest_cache", ".coverage", "htmlcov",
    ".idea", ".vscode", "venv", ".venv", "env", ".egg-info", ".matplotlib"
}

def should_ignore(rel_path: str) -> bool:
    parts = rel_path.replace("\\", "/").split("/")
    for part in parts:
        if part in IGNORE_PATTERNS or part.endswith(".pyc") or part.endswith(".pyo"):
            return True
    return False

def get_all_project_files(base_dir: str):
    file_list = []
    for root, dirs, files in os.walk(base_dir):
        # Filter out ignored directories
        dirs[:] = [d for d in dirs if d not in IGNORE_PATTERNS]
        for f in files:
            full_path = os.path.join(root, f)
            rel_path = os.path.relpath(full_path, base_dir).replace("\\", "/")
            if not should_ignore(rel_path):
                file_list.append((rel_path, full_path))
    return file_list

def upload_repo(token: str, repo_name: str, is_private: bool = False):
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github.v3+json",
        "X-GitHub-Api-Version": "2022-11-28"
    }

    print(">> [1/5] Authenticating with GitHub API...")
    user_res = requests.get("https://api.github.com/user", headers=headers)
    if user_res.status_code != 200:
        print(f"Error: Authentication failed ({user_res.status_code}): {user_res.text}")
        sys.exit(1)

    username = user_res.json()["login"]
    print(f"  -> Authenticated as GitHub user: @{username}")

    print(f"\n>> [2/5] Checking or creating repository: {username}/{repo_name}...")
    repo_check = requests.get(f"https://api.github.com/repos/{username}/{repo_name}", headers=headers)
    
    if repo_check.status_code == 404:
        # Create repository
        create_payload = {
            "name": repo_name,
            "description": "FinGuard AI: Enterprise Real-Time Bank Fraud Detection Platform using XGBoost, SHAP & FastAPI",
            "private": is_private,
            "auto_init": False
        }
        create_res = requests.post("https://api.github.com/user/repos", headers=headers, json=create_payload)
        if create_res.status_code not in (200, 201):
            print(f"Error creating repository ({create_res.status_code}): {create_res.text}")
            sys.exit(1)
        print(f"  -> Repository '{repo_name}' created successfully on GitHub!")
    elif repo_check.status_code == 200:
        print(f"  -> Repository '{username}/{repo_name}' already exists. Will update main branch.")
    else:
        print(f"Error checking repository ({repo_check.status_code}): {repo_check.text}")
        sys.exit(1)

    files = get_all_project_files(PROJECT_ROOT)
    print(f"\n>> [3/5] Uploading {len(files)} project files to GitHub Git Tree...")

    tree_items = []
    for idx, (rel_path, full_path) in enumerate(files, 1):
        print(f"  [{idx}/{len(files)}] Uploading {rel_path}...", end="", flush=True)
        try:
            with open(full_path, "rb") as f:
                content_bytes = f.read()
            content_b64 = base64.b64encode(content_bytes).decode("utf-8")
        except Exception as e:
            print(f" [SKIP - read error: {e}]")
            continue

        blob_payload = {
            "content": content_b64,
            "encoding": "base64"
        }
        blob_res = requests.post(f"https://api.github.com/repos/{username}/{repo_name}/git/blobs", headers=headers, json=blob_payload)
        if blob_res.status_code not in (200, 201):
            print(f" [FAILED: {blob_res.status_code}]")
            continue

        blob_sha = blob_res.json()["sha"]
        tree_items.append({
            "path": rel_path,
            "mode": "100644",
            "type": "blob",
            "sha": blob_sha
        })
        print(" [OK]")

    if not tree_items:
        print("Error: No files were successfully staged for upload.")
        sys.exit(1)

    print(f"\n>> [4/5] Creating Git Tree and Commit...")
    # Get parent commit if repository has history
    ref_res = requests.get(f"https://api.github.com/repos/{username}/{repo_name}/git/ref/heads/main", headers=headers)
    parent_sha = None
    if ref_res.status_code == 200:
        parent_sha = ref_res.json()["object"]["sha"]

    tree_payload = {"tree": tree_items}
    tree_res = requests.post(f"https://api.github.com/repos/{username}/{repo_name}/git/trees", headers=headers, json=tree_payload)
    if tree_res.status_code not in (200, 201):
        print(f"Error creating tree: {tree_res.text}")
        sys.exit(1)
    tree_sha = tree_res.json()["sha"]

    commit_payload = {
        "message": "Initial commit: FinGuard AI Bank Fraud Detection Platform",
        "tree": tree_sha,
        "parents": [parent_sha] if parent_sha else []
    }
    commit_res = requests.post(f"https://api.github.com/repos/{username}/{repo_name}/git/commits", headers=headers, json=commit_payload)
    if commit_res.status_code not in (200, 201):
        print(f"Error creating commit: {commit_res.text}")
        sys.exit(1)
    new_commit_sha = commit_res.json()["sha"]

    print(f"\n>> [5/5] Updating 'main' branch reference...")
    if parent_sha:
        update_ref = requests.patch(
            f"https://api.github.com/repos/{username}/{repo_name}/git/refs/heads/main",
            headers=headers,
            json={"sha": new_commit_sha, "force": True}
        )
    else:
        update_ref = requests.post(
            f"https://api.github.com/repos/{username}/{repo_name}/git/refs",
            headers=headers,
            json={"ref": "refs/heads/main", "sha": new_commit_sha}
        )

    if update_ref.status_code in (200, 201):
        repo_url = f"https://github.com/{username}/{repo_name}"
        print("=" * 65)
        print(f"SUCCESS! Codebase successfully uploaded to GitHub:")
        print(f"--> {repo_url}")
        print("=" * 65)
    else:
        print(f"Error updating main ref: {update_ref.text}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Upload codebase directly to GitHub.")
    parser.add_argument("--token", type=str, default=os.environ.get("GITHUB_TOKEN"), help="GitHub Personal Access Token (classic with repo scope or fine-grained)")
    parser.add_argument("--repo", type=str, default="bank-fraud-detection", help="Repository name (default: bank-fraud-detection)")
    parser.add_argument("--private", action="store_true", help="Set repository to private (default: public)")
    args = parser.parse_args()

    token = args.token
    if not token:
        token = input("Enter your GitHub Personal Access Token (with 'repo' scope): ").strip()

    if not token:
        print("Error: A GitHub Personal Access Token is required.")
        sys.exit(1)

    upload_repo(token=token, repo_name=args.repo, is_private=args.private)
