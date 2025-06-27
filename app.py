#
#   Visect
#          - a tool to automatically find Bisect in V8 (the commit which caused the bug)
#          
#          by @streypaws
#

import os
from utils.colors import *
from utils.git import is_git_installed, extract_git_diffs_to_db
from base.compiler import compile_v8
from base.bisect import *
from base.query import search_string_in_db
from utils.system import detect_os, ensure_env_path, ensure_ripgrep_installed

# Load .env to load V8_PATH (if saved)
# Variable to hold path to V8 src
V8_PATH = None
# Variable to hold the OS on which this script runs
OS = None 
# Variable to hold DB path for Commit Text Search (Method 2)
DB_PATH = "db/"

def display_banner():
    print()
    green("\ \   / (_)___  ___  ___| |_ ")
    green(" \ \ / /| / __|/ _ \/ __| __|")
    green("  \ V / | \__ \  __/ (__| |_ ")
    green("   \_/  |_|___/\___|\___|\__|")
    print()
    print()
    green("                             by StreyPaws")
    print()
    print()

def display_menu():
    magenta("\nMenu:")
    magenta("========================================")
    magenta("1. Find Bisect for your bug/crash poc")
    magenta("2. Query Commit Code")
    magenta(f"3. Compile V8 for {OS} [debug/release]")
    magenta("4. Exit")

def initialize():
    global V8_PATH, OS
    V8_PATH = ensure_env_path()
    
    OS = detect_os()
    is_git_installed(OS)
    ensure_ripgrep_installed(OS)
    extract_git_diffs_to_db(DB_PATH,V8_PATH)

    os.makedirs("test", exist_ok=True)
    crash_log_path = "test/crash.log"
    if os.path.exists(crash_log_path):
        os.remove(crash_log_path)
        green("[+] Removed old crash.log")

def main():

    display_banner()
    initialize()

    while True:
        display_menu()
        print()
        choice = yellow_input("Enter your choice (1/2/3/4): ")

        if choice == '1':
            find_bisect(V8_PATH,DB_PATH,OS)
        elif choice == '2':
            search_string_in_db(DB_PATH)
        elif choice == '3':
            compile_v8(V8_PATH,OS)
        elif choice == '4':
            print()
            magenta("Bye :)")
            print()
            break
        else:
            print()
            red("[-] Invalid choice. Please try again.")
            print()


if __name__ == "__main__":
    main()