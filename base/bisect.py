import os, sys, re, shutil
import subprocess
import zipfile
import requests
from tqdm import tqdm
from time import time
import math

from base.util import get_cr_commit_position_and_date
from utils.flags import validate_flags
from utils.colors import *
from utils.system import is_internet_working
from utils.git import *

# Variable to hold path to poc.js under test (make sure this test produces a deterministic BAD)
POC_PATH = "test/test.js"
# Variable to hold the hash under which the poc produces a crash
BAD_COMMIT = None
# Variable to hold the hash under which the poc doesn't produce a crash
GOOD_COMMIT = None
# Variable to hold the Default speculated Distance between the BAD_COMMIT and the Bisect Commit (Default:1024)
DISTANCE = 1024
# Link to Download D8 from a commit hash
D8_LINK = None
# Define Target to find bisect on (debug/release)
TARGET = None
# Define V8 Repo Path
V8_PATH = None
# Define DB Path
DB_PATH = None
# Define Time Array for ETA Specualtion
TIME_ARRAY = []

def download_and_extract_d8(commit_hash):
    # Validate revision
    revision, date = get_cr_commit_position_and_date(commit_hash,DB_PATH)
    if not re.fullmatch(r"\d{5,6}", str(revision)):
        red("[-] Invalid revision number. Must be 5 or 6 digits.")
        return

    # Setup paths
    base_dir = "testarea"
    zip_path = os.path.join(base_dir, "test.zip")
    extract_dir = os.path.join(base_dir, "test")

    # Create/empty base directory
    os.makedirs(base_dir, exist_ok=True)
    if os.path.exists(zip_path):
        os.remove(zip_path)
    if os.path.isdir(extract_dir):
        shutil.rmtree(extract_dir)

    # Format the download URL
    download_url = D8_LINK.replace("@", str(revision))

    yellow(f"[*] Downloading revision {revision}...")
    print()

    try:
        is_internet_working()
        # Using requests with tqdm progress bar
        with requests.get(download_url, stream=True) as r:
            r.raise_for_status()
            total = int(r.headers.get('content-length', 0))
            with open(zip_path, 'wb') as f, tqdm(
                total=total, unit='B', unit_scale=True, desc="Downloading"
            ) as pbar:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                        pbar.update(len(chunk))
    except:
        red("[-] V8 Download Failed!")
        sys.exit(1)
        

    # Extract zip
    print()
    yellow("[*] Extracting file for analysis...")
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        zip_ref.extractall(extract_dir)

    # Clean up
    os.remove(zip_path)
    green("[+] Done. Extracted to "+extract_dir)

def run_d8_with_args(custom_args):
    d8_path = "testarea/test/d8"
    assert os.path.isfile(d8_path), f"[-] d8 binary not found at {d8_path}"

    # Ensure d8 is executable
    try:
        subprocess.run(["chmod", "+x", d8_path], check=True)
        green(f"[+] Made {d8_path} executable.")
    except subprocess.CalledProcessError:
        red(f"[-] Failed to chmod +x {d8_path}")
        return

    # Check or create tests/test.js
    test_js_path = "test/test.js"
    os.makedirs(os.path.dirname(test_js_path), exist_ok=True)
    if not os.path.exists(test_js_path):
        with open(test_js_path, "w") as f:
            f.write('var a = 42;')
        green("[+] Created test/test.js")

    # Dry-run with test.js
    yellow("[*] Running d8 with test.js to verify setup...")
    try:
        subprocess.run(
            [d8_path] + custom_args.split() + [test_js_path],
            check=True
        )
        green("[+] test.js executed successfully.")
    except subprocess.CalledProcessError:
        red("[-] Error running d8 with test.js. Check d8 binary or arguments.")
        return

    # Run with PoC and log crash if any
    yellow("[*] Running d8 with PoC and checking for crash...")
    try:
        result = subprocess.run(
            [d8_path] + custom_args.split() + [POC_PATH],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True
        )

        base_dir = "testarea"
        zip_path = os.path.join(base_dir, "test.zip")
        extract_dir = os.path.join(base_dir, "test")
        os.makedirs(base_dir, exist_ok=True)
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.isdir(extract_dir):
            shutil.rmtree(extract_dir)

        if result.returncode != 0:
            # Log output only on crash or error
            if result.returncode != 1: # Generic Errors
                os.makedirs("test", exist_ok=True)
                with open("test/crash.log", "w") as f:
                    f.write(result.stdout)
                light_red(f"[-] d8 crashed with return code {result.returncode}. Output saved to test/crash.log.")
                return -1
            else:
                return 1
        else:
            green("[+] d8 ran successfully with PoC.")
            return 0
    except Exception as e:
        red("[-] Exception while running PoC:", e)
        sys.exit(1)

def find_bisect(v8_path,db_path,OS): # Method 1 :TODO
    global POC_PATH, TARGET, D8_LINK, V8_PATH, DB_PATH, BAD_COMMIT, GOOD_COMMIT, TIME, TIME_ARRAY
    V8_PATH = v8_path
    DB_PATH = db_path
    custom_args = None
    speculate = 0
    TIME = 0
    TIME_ARRAY = []

    while True:
        POC_PATH = yellow_input(f"Enter the path for Crash PoC: ").strip()
        if not os.path.exists(POC_PATH):
            red("[-] Path does not exist. Try again.")
        else:
            break
        print()

    while True:
        choice = yellow_input("Input Target (debug/release): ")

        if (choice.lower() == "debug") or (choice.lower() == "release"):
            TARGET = choice
            break
        
        red("[-] Invalid Target. Please try again.")
        print()

    if OS == "x64":
        D8_LINK = f"https://www.googleapis.com/download/storage/v1/b/v8-asan/o/linux-{TARGET}%2Fd8-linux-{TARGET}-v8-component-@.zip?alt=media"
    
    elif OS == "w64":
        D8_LINK = f"https://www.googleapis.com/download/storage/v1/b/v8-asan/o/win64-{TARGET}%2Fd8-asan-win64-{TARGET}-v8-component-@.zip?alt=media"
    else:
        red("[-] Unsupported OS for v8 download. Exiting...")
        sys.exit(1)

    ## Enter BAD BISECT
    while True:
        choice = yellow_input("Input Commit Hash on which PoC Crashes (BAD_COMMIT): ")
        print()
        choice = choice[:11]
        if is_commit_in_log(choice,V8_PATH):
            BAD_COMMIT = choice
            break
        
        red("[-] Invalid Commit Hash. Please try again.")

    while True:
        choice = yellow_input("Input custom arguments for d8 (space seperated like: \"--allow-natives-syntax --future\"): ")

        if validate_flags(choice) != "":
            custom_args = choice
            break
        
        red("[-] Invalid Arguments. Please try again.")
        print()
    
    # Check if BAD_COMMIT is Valid
    yellow(f"[*] Trying to reproduce crash on {BAD_COMMIT} with {custom_args} flags...")
    start1 = time()
    download_and_extract_d8(BAD_COMMIT)
    ret = run_d8_with_args(custom_args)
    end1 = time()
    green(f"[+] BAD_COMMIT Validation executed in {end1 - start1:.4f} seconds")
    TIME_ARRAY.append(end1-start1)
    # print(ret)

    if ret in [0,1]:
        red("[-] d8 ran with some error other than a Crash. Please check the Testcase (were flags put correctly?)")   
        sys.exit(1)
    else:
        green(f"[+] BAD_COMMIT Validated! Setting {BAD_COMMIT} as BAD_COMMIT.")

    ## Enter GOOD BISECT
    print()
    while True:
        choice = yellow_input("Input Commit Hash on which PoC Doesn't Crash (If you don't know just put \"None\"): ")
        print()

        choice = choice[:11]

        if choice.lower() == "none":
            # Speculate
            yellow(f"[*] Speculating GOOD_COMMIT by moving {DISTANCE} spaces behind...")   
            GOOD_COMMIT = get_commit(BAD_COMMIT,DISTANCE,V8_PATH)
            speculate = 1
            break
        elif is_commit_in_log(choice,V8_PATH):
            GOOD_COMMIT = choice
            break
        
        red("[-] Invalid Commit Hash or Keyword. Please try again.")

    dist = get_distance(GOOD_COMMIT,BAD_COMMIT,V8_PATH)
    if dist == 0:
        red("[-] Bad commit is behind Good commit, this either happens if the bug is patched in the Good commit or you put the data in reverse.")
        red("[-] Either way, continuing will not give you the correct bisect. Hence bailing... Please check the data and try again.")
        sys.exit(1)

    # Check if GOOD_COMMIT is Valid
    while True:
        yellow(f"[*] Trying to reproduce crash on {GOOD_COMMIT} ...")

        start2 = time()
        download_and_extract_d8(GOOD_COMMIT)
        ret = run_d8_with_args(custom_args)
        end2 = time()

        green(f"[+] GOOD_COMMIT Validation executed in {end2 - start2:.4f} seconds")
        TIME_ARRAY.append(end2-start2)

        if speculate:
            if ret not in [0,1]:
                # Speculate Again
                red(f"[-] d8 ran with a Crash. Speculating GOOD_COMMIT again by moving {DISTANCE} spaces")   
                GOOD_COMMIT = get_commit(GOOD_COMMIT,DISTANCE,V8_PATH)
            else:
                green(f"[+] GOOD_COMMIT Found! Setting {GOOD_COMMIT} as GOOD_COMMIT.")
                break
        else:
            if ret not in [0,1]:
                red("[-] d8 ran with a Crash. Please check the Testcase (were flags put correctly?)")   
                sys.exit(1)
            else:
                green(f"[+] GOOD_COMMIT Validated! Setting {GOOD_COMMIT} as GOOD_COMMIT.")
                break
    
    TIME = sum(TIME_ARRAY) / len(TIME_ARRAY)
    onetime = TIME

    print()
    yellow("[*] Starting Bisect Process...")
    print()

    # Number of Passes
    count = int(math.log2(dist)) + 1
    TIME = TIME * count

    # Start bisect
    while True:
        d = get_distance(GOOD_COMMIT,BAD_COMMIT,V8_PATH)

        if d <= 1:
            break

        eta_minutes = int(TIME // 60)
        eta_seconds = int(TIME % 60)
        print()
        magenta("==================================================")
        magenta("|                                                |")
        magenta(f"|     ETA: {eta_minutes} min {eta_seconds} sec (approx {count} passes)       |")
        magenta("|                                                |")
        magenta("==================================================")
        print()

        d = int(d/2)

        commit_center = get_commit(BAD_COMMIT,d,V8_PATH)

        if commit_center == BAD_COMMIT or commit_center == GOOD_COMMIT:
            yellow("[*] Commit center has converged with BAD or GOOD — bisect complete.")
            break

        yellow(f"[*] Trying to reproduce crash on {commit_center} [{d} away from {BAD_COMMIT}]...")

        download_and_extract_d8(commit_center)
        ret = run_d8_with_args(custom_args)

        if ret not in [0,1]:
            light_red(f"[-] d8 ran with a Crash. Setting BAD_COMMIT to {commit_center}")   
            BAD_COMMIT = commit_center
        else:
            green(f"[+] d8 ran without a Crash. Setting GOOD_COMMIT to {commit_center}.")
            GOOD_COMMIT = commit_center

        TIME = TIME - onetime
        count-=1
        

    url = f"https://chromium.googlesource.com/v8/v8/+/{BAD_COMMIT}"
    link = f"\033]8;;{url}\a{BAD_COMMIT}\033]8;;\a"
    rev, date_str = get_cr_commit_position_and_date(BAD_COMMIT,db_path)
    print()
    green("=======================================================================================")
    green("|                                                                                     |")
    green(f"| Bisect Found -> {link:<45} Revision: {str(rev):<7} Date: {str(date_str)}  |")
    green("|                                                                                     |")
    green("=======================================================================================")
    print()


