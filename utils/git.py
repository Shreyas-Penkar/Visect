import os
import sys, re
import subprocess, shutil
from tqdm import tqdm
import multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

from utils.colors import *

def is_git_installed(system):
    try:
        subprocess.run(["git", "--version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
        green("[+] Git is installed.")
    except (subprocess.CalledProcessError, FileNotFoundError):
        yellow("[*] Git not found. Trying to install it...")
        if system == "x64":
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "git"], check=True)
        else:
            red("[-] Unsupported OS for auto-installation.")
            return False

        if shutil.which("git"):
            green("[+] git installed successfully.")
            return True
        else:
            red("[-] git installation failed. Exiting...")
            sys.exit(1)

def is_valid_commit_hash(commit_hash):
    # Check if it's 11 to 40 hex characters (common git short or full hashes)
    pattern = r'^[0-9a-f]{11,40}$'
    return bool(re.fullmatch(pattern, commit_hash.lower()))

def is_commit_in_log(commit_hash,v8_path):
    try:
        if not is_valid_commit_hash(commit_hash):
            red("[-] Your commit hash should be atleast 11-40 characters long.")
            return False
        
        cmd = f"git log --oneline | grep {commit_hash}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=v8_path 
        )
        
        if result.stdout:
            green("[+] Commit Found: "+result.stdout.strip())
            print()
            return True
        else:
            return False
            
    except Exception as e:
        red(f"Error: {e}")
        return False

def save_commit_diff(commit_hash,db_path,v8_path):
    diff_file_path = os.path.join(db_path, f"{commit_hash}.diff")

    if os.path.isfile(diff_file_path):
        return True  # Already exists, skip

    try:
        with open(diff_file_path, "w") as diff_file:
            subprocess.run(
                ["git", "show", commit_hash],
                cwd=v8_path,
                stdout=diff_file,
                stderr=subprocess.DEVNULL,
                text=True,
                check=True
            )
        return True
    except Exception as e:
        return f"Error for {commit_hash}: {e}"    
    
def get_commit(start_hash,distance,v8_path):
    try:
        yellow(f"[*] Getting the commit {distance} behind {start_hash}...")

        cmd = [
            "git",
            "log",
            start_hash,
            "--oneline",
            "-n",
            str(distance+1)
        ]

        result = subprocess.run(
            cmd,
            cwd=v8_path,
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().splitlines()

        if len(lines) < distance:
            red(f"[-] Less than {distance} commits found from the given hash.")
            sys.exit(1)

        target_line = lines[-1]  
        return target_line.split()[0]

    except subprocess.CalledProcessError as e:
        red(f"[-] Git command failed: {e.stderr}")
        return None
    except Exception as e:
        red(f"[-] Error: {e}")
        return None
    
def get_distance(older_commit, newer_commit, repo_path):
    try:
        yellow(f"[*] Calculating distance from {older_commit} to {newer_commit}...")

        cmd = [
            "git",
            "rev-list",
            "--count",
            f"{older_commit}..{newer_commit}"
        ]

        result = subprocess.run(
            cmd,
            cwd=repo_path,
            capture_output=True,
            text=True,
            check=True
        )

        distance = int(result.stdout.strip())
        green(f"[+] {newer_commit} is {distance} commits ahead of {older_commit}")
        return distance

    except subprocess.CalledProcessError as e:
        red(f"[-] Git command failed: {e.stderr}")
        return None
    except Exception as e:
        red(f"[-] Error: {e}")
        return None

def extract_git_diffs_to_db(db_path,v8_path):
    try:
        yellow("[*] Checking if DB is upto date...")
        os.makedirs(db_path, exist_ok=True)

        # Get all commit hashes
        result = subprocess.run(
            ["git", "log", "--pretty=format:%h"],
            cwd=v8_path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            check=True
        )

        all_commits = result.stdout.strip().splitlines()

        # Filter out existing ones
        missing_commits = [
            ch for ch in all_commits
            if not os.path.isfile(os.path.join(db_path, f"{ch}.diff"))
        ]

        total = len(missing_commits)

        if total == 0:
            green("[+] All commit diffs are already up to date.")
            return True

        green(f"[+] Found {total} new commits. Saving to DB using {multiprocessing.cpu_count()} cores...")

        with ProcessPoolExecutor() as executor:
            futures = {executor.submit(save_commit_diff, ch,db_path,v8_path): ch for ch in missing_commits}
            for f in tqdm(as_completed(futures), total=total, desc="Updating DB", unit="commit"):
                result = f.result()
                if result is not True:
                    print(result)

        green(f"[+] Done: {total} new commit diffs saved to: {db_path}")
        return True

    except subprocess.CalledProcessError as e:
        red(f"[-] Git command failed: {e.stderr}")
        return False
    except Exception as e:
        red(f"[-] Unexpected error: {e}")
        return False