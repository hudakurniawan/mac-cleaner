import os
import subprocess
import threading
from send2trash import send2trash

# Global state lock to prevent concurrent deletion collisions
_deletion_lock = threading.Lock()

def run_command(command, use_sudo=False):
    if use_sudo:
        command = f"sudo {command}"
    try:
        if use_sudo:
            result = subprocess.run(command, shell=True)
            return "" if result.returncode == 0 else f"Error: {result.returncode}"
        else:
            result = subprocess.run(command, shell=True, capture_output=True, text=True)
            return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def is_protected_path(path):
    """Extra safety layer to prevent deleting core system or cloud folders."""
    protected = [
        "/System", 
        "/Library", # We only allow specific subfolders, not the root
        os.path.expanduser("~/Library"),
        os.path.expanduser("~"),
        "/",
        os.path.expanduser("~/Documents"),
        os.path.expanduser("~/Desktop"),
        os.path.expanduser("~/Downloads"),
        os.path.expanduser("~/Pictures"),
        os.path.expanduser("~/Library/CloudStorage")
    ]
    # Exact match prevention
    if path in protected:
        return True
    return False

def delete_items(items):
    """Deletes confirmed items safely, using send2trash where possible."""
    if not _deletion_lock.acquire(blocking=False):
        raise Exception("A deletion process is already running. Please wait.")
    
    results = []
    user_home = os.path.expanduser("~")
    
    try:
        for item in items:
            if is_protected_path(item):
                results.append({"item": item, "status": "failed", "reason": "Protected path"})
                continue

            try:
                if item.startswith("PACKAGE_RECEIPT:"):
                    pkg_id = item.split(":")[1]
                    run_command(f"pkgutil --forget {pkg_id}", use_sudo=True)
                    results.append({"item": item, "status": "success", "method": "pkgutil"})
                elif item.startswith(user_home):
                    # For user-owned files, move to Trash via send2trash (native APIs)
                    send2trash(item)
                    results.append({"item": item, "status": "success", "method": "trash"})
                else:
                    # System-level files (not in ~/) usually require sudo
                    run_command(f'rm -rf "{item}"', use_sudo=True)
                    results.append({"item": item, "status": "success", "method": "sudo rm"})
            except Exception as e:
                results.append({"item": item, "status": "failed", "reason": str(e)})
    finally:
        _deletion_lock.release()
        
    return results
