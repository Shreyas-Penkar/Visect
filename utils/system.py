import sys, shutil
import subprocess
import socket
import platform, os
from dotenv import load_dotenv, set_key
from utils.colors import *

def is_internet_working(host="www.google.com", port=80, timeout=3):
    try:
        socket.setdefaulttimeout(timeout)
        socket.create_connection((host, port))
    except OSError:
        red("[-] No internet connection.")
        sys.exit(1)

def ensure_ripgrep_installed(system):
    if shutil.which("rg"):
        green("[+] ripgrep is already installed.")
        return True

    yellow(f"[*] ripgrep not found. Attempting installation on {system}...")
    is_internet_working()

    try:
        if system == "x64":
            subprocess.run(["sudo", "apt", "update"], check=True)
            subprocess.run(["sudo", "apt", "install", "-y", "ripgrep"], check=True)
        else:
            red("[-] Unsupported OS for auto-installation.")
            return False

        if shutil.which("rg"):
            green("[+] ripgrep installed successfully.")
            return True
        else:
            red("[-] ripgrep installation failed. Query Commits (Option 2) will not work properly.")
            return False

    except subprocess.CalledProcessError as e:
        red(f"[-] Error during installation: {e}")
        return False
    
def detect_os():
    os_name = platform.system()

    if os_name == "Darwin":
        green("[+] MacOS is not supported yet. Bailing...")
        sys.exit(1)
    elif os_name == "Linux":
        green("[+] Linux Detected. Setting it as target OS")
        target_cpu = "x64"
    elif os_name == "Windows":
        red("[-] Windows is not supported yet. Bailing...S")
        sys.exit(1)
    else:
        red(f"[-] Unknown OS: {os_name}. Bailing...")
        sys.exit(1)

    return target_cpu

def is_valid_v8_directory(path):
    # Minimal set of required files/dirs for a valid V8 repo
    required_items = ["DEPS", "BUILD.gn", "README.md", "src", "tools"]
    return all(os.path.exists(os.path.join(path, item)) for item in required_items)

def ensure_env_path(var_name="V8_PATH", env_file=".env"):
    # Load existing environment variables from .env
    load_dotenv(env_file)

    path_val = os.getenv(var_name)

    if path_val and os.path.exists(path_val) and is_valid_v8_directory(path_val):
        green(f"[+] {var_name} is set (from .env): {path_val}")
        return path_val

    red(f"[-] {var_name} not found.")

    while True:
        user_input = yellow_input(f"Enter the path for V8 Repository (only needed once): ").strip()
        if not os.path.exists(user_input):
            red("[-] Path does not exist. Try Again.")
        elif not is_valid_v8_directory(user_input):
            red("[-] Path exists but does not appear to be a valid V8 repository.")
        else:
            break
        print()

    # Ensure .env file exists
    if not os.path.exists(env_file):
        with open(env_file, "w") as f:
            f.write("")  # create empty .env

    # Save to .env file
    set_key(env_file, var_name, user_input)
    green(f"[+] {var_name} saved to {env_file}")

    return user_input