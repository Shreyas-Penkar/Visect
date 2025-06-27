import os
import sys
import subprocess

from base.util import get_gn_args
from utils.colors import *
from utils.git import *
from utils.system import is_internet_working

# Global configuration variables
OS = None
V8_PATH = None
IS_DEBUG = None

def run_gclient_sync():
    try:
        is_internet_working()
        yellow("[*] Running 'gclient sync -D'...")

        process = subprocess.Popen(
            ["gclient", "sync", "-D"],
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            green("[+] gclient sync completed successfully.")
            return True
        else:
            red("[-] gclient sync failed. Is depot_tools in PATH? Bailing...")
            sys.exit(1)

    except Exception as e:
        red(f"[ERROR] gclient sync failed: {e}")
        return False

def git_checkout_commit(commit_hash):
    try:
        is_internet_working()

        if commit_hash.lower() == 'latest':
            commit_hash = 'main'
        yellow(f"[*] Checking out commit {commit_hash}...")

        cmd = ["git", "checkout", commit_hash]
        process = subprocess.Popen(
            cmd,
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode != 0:
            red("[-] Git checkout failed. Please check your V8 repo. Bailing...")
            sys.exit(1)

        green(f"[+] Checked out to {commit_hash}")

        if commit_hash == "main":
            is_internet_working()
            yellow("[*] Pulling latest changes from origin/main...")
            pull_cmd = ["git", "pull"]
            pull_process = subprocess.Popen(
                pull_cmd,
                cwd=V8_PATH,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )

            for line in pull_process.stdout:
                print(line, end="")

            pull_process.wait()

            if pull_process.returncode == 0:
                green("[+] Successfully pulled latest changes.")
            else:
                red("[-] Git pull failed.")
                sys.exit(1)

        return True

    except Exception as e:
        red(f"[ERROR] git checkout failed: {e}")
        return False

def run_gn_gen():
    try:
        gn_args = get_gn_args(OS, IS_DEBUG)
        yellow(f"[*] Running 'gn gen out/{OS}.{IS_DEBUG}'...")

        cmd = [
            "gn",
            "gen",
            f"out/{OS}.{IS_DEBUG}",
            f'--args={gn_args.replace(chr(10), " ").strip()}'
        ]

        process = subprocess.Popen(
            cmd,
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            green(f"[+] GN gen for {IS_DEBUG} completed successfully.")
            return True
        else:
            red(f"[-] GN gen failed. Check the GN args and setup.")
            sys.exit(1)

    except Exception as e:
        red(f"[ERROR] GN gen failed: {e}")
        return False

def run_ninja_build():
    try:
        out_dir = f"out/{OS}.{IS_DEBUG}"
        full_out_path = os.path.join(V8_PATH, out_dir)

        if not os.path.isdir(full_out_path):
            red(f"[-] Output directory does not exist: {full_out_path}")
            sys.exit(1)

        yellow(f"[*] Running 'ninja -C {out_dir}'...")

        cmd = ["ninja", "-C", out_dir]

        process = subprocess.Popen(
            cmd,
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            green("[+] Ninja build completed successfully.")
            return True
        else:
            red("[-] Ninja build failed.")
            sys.exit(1)

    except Exception as e:
        red(f"[ERROR] Ninja build failed: {e}")
        return False

def compile_v8(v8_path,os):
    global IS_DEBUG, V8_PATH, OS

    V8_PATH = v8_path
    OS = os

    while True:
        commit_hash = yellow_input("Input Commit HASH (or 'latest' to get latest commit): ").strip()
        if commit_hash.lower() == "latest" or is_commit_in_log(commit_hash, V8_PATH):
            break
        red("[-] Invalid commit hash. Please try again.")
        print()

    while True:
        target = yellow_input("Input Target (debug/release): ").strip().lower()
        if target in ["debug", "release"]:
            IS_DEBUG = target
            break
        red("[-] Invalid target. Please try again.")
        print()

    git_checkout_commit(commit_hash)
    run_gclient_sync()
    run_gn_gen()
    run_ninja_build()

    green(f"[+] V8 compiled successfully for {OS}.{IS_DEBUG}")
    print()
