#
#   Visect
#          - a tool to find Bisect in V8 (the commit which caused the bug)
#          
#          by @streypaws
#

import os, sys, re
import subprocess
import socket

# Define path to V8 src
V8_PATH = "/home/br4v3h3r0/v8/v8"
# Define path to poc.js under test (make sure this test produces a deterministic BAD)
POC_PATH = "/home/br4v3h3r0/poc.js"
# Define the hash under which the poc produces a BAD
BAD_COMMIT = "f5fba01"
# Define the Default speculated Distance between the BAD_COMMIT and the Bisect Commit (Default:128)
DISTANCE = 128
# Define whether the test should happen in Debug (x64.debug) or Release (x64.release) Build (Default: debug)
TEST_BUILD = "debug"
# Define args.gn for debug and release version
GN_ARGS_DEBUG = """
is_component_build = true
is_debug = true
symbol_level = 2
target_cpu = "x64"
v8_enable_backtrace = true
v8_enable_fast_mksnapshot = true
v8_enable_slow_dchecks = true
v8_optimized_debug = false
"""

GN_ARGS_RELEASE = """
is_component_build = false
is_debug = false
target_cpu = "x64"
v8_enable_sandbox = true
v8_enable_backtrace = true
v8_enable_disassembler = true
v8_enable_object_print = true
v8_enable_verify_heap = true
dcheck_always_on = false
"""

def is_internet_working(host="www.google.com", port=80, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.create_connection((host, port))
        print("[+] Internet connection is working.")
        return True
    except OSError:
        print("[-] No internet connection.")
        return False

def is_valid_commit_hash(commit_hash):
    # Check if it's 7 to 40 hex characters (common git short or full hashes)
    pattern = r'^[0-9a-f]{7,40}$'
    return bool(re.fullmatch(pattern, commit_hash.lower()))

def is_commit_in_log(commit_hash):
    try:
        if not is_valid_commit_hash(BAD_COMMIT):
            print("[-] Input is not a commit hash. Bailing...")
            sys.exit(1)
        cmd = f"git log --oneline | grep {commit_hash}"
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            cwd=V8_PATH  
        )
        
        if result.stdout:
            print("[+] Commit Found: ",result.stdout.strip())
        else:
            print("[-] No matching commit found in log. Bailing...")
            sys.exit(1)
        
        return result.returncode == 0
    
    except Exception as e:
        print(f"Error: {e}")
        return False

def run_gclient_sync():
    try:
        print("[*] Running 'gclient sync -D'...")

        process = subprocess.Popen(
            ["gclient", "sync", "-D"],
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        # Stream the output line by line
        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            print("[+] gclient sync completed successfully.")
            return True
        else:
            print("[-] gclient sync failed. Please check if gclient sync is working properly (Is depot_tools in PATH?). Bailing...")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        return False

def git_checkout_commit(commit_hash):
    try:
        if not is_valid_commit_hash(commit_hash):
            print("[-] Input is not a valid commit hash. Bailing...")
            sys.exit(1)

        print(f"[*] Checking out commit {commit_hash}...")

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

        if process.returncode == 0:
            print(f"[+] Successfully checked out to commit {commit_hash}.")
            return True
        else:
            print("[-] Git checkout failed. Please check your V8 repo. Bailing...")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        return False
    
def run_gn_gen():
    try:
        if not os.path.isdir(V8_PATH):
            print(f"[-] Invalid V8 path: {V8_PATH}")
            sys.exit(1)

        # Select GN args based on TEST_BUILD
        if TEST_BUILD.lower() == "debug":
            gn_args = GN_ARGS_DEBUG
        elif TEST_BUILD.lower() == "release":
            gn_args = GN_ARGS_RELEASE

        print(f"[*] Running 'gn gen x64.bisect' for {TEST_BUILD} build...")

        cmd = [
            "gn",
            "gen",
            "out/x64.bisect",
            f'--args={gn_args.replace(chr(10), " ").strip()}'
        ]

        process = subprocess.Popen(
            cmd,
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            print(f"[+] GN gen for {TEST_BUILD} build completed successfully.")
            return True
        else:
            print(f"[-] GN gen for {TEST_BUILD} build failed. Please check if it is working properly. Bailing...")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        return False
    
def get_commit(start_hash):
    try:
        print(f"[*] Getting the commit {DISTANCE} behind {start_hash}...")

        cmd = [
            "git",
            "log",
            start_hash,
            "--oneline",
            "-n",
            str(DISTANCE)
        ]

        result = subprocess.run(
            cmd,
            cwd=V8_PATH,
            capture_output=True,
            text=True,
            check=True
        )

        lines = result.stdout.strip().splitlines()

        if len(lines) < DISTANCE:
            print("[-] Less than 129 commits found from the given hash.")
            sys.exit(1)

        target_line = lines[-1]  # 128 behind
        print(f"[+] Commit {DISTANCE} behind {start_hash}:\n{target_line}")
        return target_line

    except subprocess.CalledProcessError as e:
        print(f"[-] Git command failed: {e.stderr}")
        return None
    except Exception as e:
        print(f"[-] Error: {e}")
        return None

def run_ninja_build():
    try:
        out_dir = "out/x64.bisect"
        full_out_path = os.path.join(V8_PATH, out_dir)

        if not os.path.isdir(full_out_path):
            print(f"[-] Output directory does not exist: {full_out_path}")
            sys.exit(1)

        print(f"[*] Running 'ninja -C {out_dir}'...")

        cmd = ["ninja", "-C", out_dir]

        process = subprocess.Popen(
            cmd,
            cwd=V8_PATH,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            shell=False
        )

        for line in process.stdout:
            print(line, end="")

        process.wait()

        if process.returncode == 0:
            print(f"[+] Ninja build completed successfully.")
            return True
        else:
            print("[-] Ninja build failed.")
            sys.exit(1)

    except Exception as e:
        print(f"Error: {e}")
        return False

# print(is_commit_in_log(BAD_COMMIT))
if not os.path.isdir(V8_PATH):
    print(f"[-] Invalid V8 path: {V8_PATH}")
    sys.exit(1)

if not os.path.isfile(POC_PATH):
    print(f"[-] Invalid POC path: {POC_PATH}")
    sys.exit(1)

if (not TEST_BUILD.lower() == "debug") and (not TEST_BUILD.lower() == "release"):
    print(f"[-] Invalid TEST_BUILD value: {TEST_BUILD}. Use 'debug' or 'release'.")
    sys.exit(1)

# run_gn_gen()
# run_ninja_build()
# get_commit(BAD_COMMIT)
git_checkout_commit("5851db91946")
run_gclient_sync()
run_ninja_build()