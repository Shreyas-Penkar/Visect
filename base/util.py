
import os, re

def get_gn_args(target_cpu: str, is_debug: bool) -> str:
    if is_debug:
        return f"""
        is_component_build = true
        is_debug = true
        symbol_level = 2
        target_cpu = "{target_cpu}"
        v8_enable_backtrace = true
        v8_enable_fast_mksnapshot = true
        v8_enable_slow_dchecks = true
        v8_optimized_debug = false
        """
    else:
        return f"""
        is_component_build = false
        is_debug = false
        target_cpu = "{target_cpu}"
        v8_enable_sandbox = true
        v8_enable_backtrace = true
        v8_enable_disassembler = true
        v8_enable_object_print = true
        v8_enable_verify_heap = true
        dcheck_always_on = false
        """

def get_cr_commit_position_and_date(commit_hash, db_path):
    diff_file_path = os.path.join(db_path, f"{commit_hash}.diff")
    
    try:
        with open(diff_file_path, 'r', encoding='utf-8') as f:
            diff_content = f.read()
    except Exception as e:
        # red(f"Failed to read diff file: {e}")
        return None, None

    # Extract Cr-Commit-Position
    position_match = re.search(r'Cr-Commit-Position: refs/heads/main@\{\#(\d+)\}', diff_content)
    cr_commit_position = int(position_match.group(1)) if position_match else "Not Found"

    # Extract author date
    date_match = re.search(r'^Date:\s+(.*)$', diff_content, re.MULTILINE)
    commit_datetime_str = date_match.group(1).strip() if date_match else "Not Found"

    return cr_commit_position, commit_datetime_str
