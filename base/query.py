import os
from datetime import datetime
from ripgrepy import Ripgrepy
from utils.colors import *

from base.util import get_cr_commit_position_and_date


def search_string_in_db(db_path):
    print()
    search_term = yellow_input("Input Search Term: ")

    yellow(f"[*] Searching for '{search_term}' in commit diffs...")

    try:
        rg = Ripgrepy(search_term, db_path).fixed_strings().with_filename().json()
        output = rg.run()

        if not output:
            red("[-] No results returned by ripgrep.")
            return []

        results = output.as_dict

        matching_commits = set()
        for match in results:
            if match.get("type") != "match":
                continue
            path = match["data"]["path"]["text"]
            filename = os.path.basename(path)
            if filename.endswith(".diff"):
                commit_hash = filename.replace(".diff", "")
                matching_commits.add(commit_hash)

        if matching_commits:
            green(f"[+] Found '{search_term}' in {len(matching_commits)} commits:")

            do_print = True
            if len(matching_commits) > 100:
                while True:
                    choice = yellow_input(f"[*] Search Term found in 100+ commits ({len(matching_commits)} in total), do you want to print the top 100? [Y/N] ")
                    if choice.lower() == 'y':
                        break
                    elif choice.lower() == 'n':
                        do_print = False
                        break
                    else:
                        red("[-] Invalid Input. Please Try again.")
                        print()

            if do_print:
                commits_with_meta = []

                for ch in matching_commits:
                    rev, date_str = get_cr_commit_position_and_date(ch, db_path)
                    if date_str:
                        try:
                            date_obj = datetime.strptime(date_str, "%a %b %d %H:%M:%S %Y %z")
                        except ValueError:
                            # fallback if format is slightly different or malformed
                            date_obj = None
                    else:
                        date_obj = None

                    commits_with_meta.append((ch, rev, date_str, date_obj))

                # Sort by datetime object (newest first), unknown dates go last
                commits_with_meta.sort(key=lambda x: x[3] or datetime.min, reverse=True)

                for ch, rev, date_str, _ in commits_with_meta[:100]:
                    url = f"https://chromium.googlesource.com/v8/v8/+/{ch}"
                    link = f"\033]8;;{url}\a{ch}\033]8;;\a"
                    print(f"  -> {link:<45} Revision: {str(rev):<14} Date: {str(date_str)}")

        else:
            red(f"[-] No matches found for '{search_term}'.")

        return list(matching_commits)

    except Exception as e:
        # red(f"[ERROR] Ripgrep search failed: {e}")
        for ch, rev, date_str, _ in commits_with_meta[:100]:
            url = f"https://chromium.googlesource.com/v8/v8/+/{ch}"
            link = f"\033]8;;{url}\a{ch}\033]8;;\a"
            print(f"  -> {link:<45} Revision: {str(rev):<14} Date: {str(date_str)}")
        return []
