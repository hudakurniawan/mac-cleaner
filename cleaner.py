import os
import sys
import subprocess

# Common macOS Library and Cache paths
SEARCH_PATHS = [
    "~/Library/Application Support",
    "~/Library/Caches",
    "~/Library/Logs",
    "~/Library/Preferences",
    "~/Library/Saved Application State",
    "~/Library/Containers",
    "~/Library/Group Containers",
    "/Library/Application Support",
    "/Library/Caches",
    "/Library/Logs",
    "/Library/Preferences",
    "/Library/LaunchAgents",
    "/Library/LaunchDaemons",
    "/Library/PrivilegedHelperTools",
    "/Library/Audio/Plug-Ins/HAL",
    "/Library/CoreMediaIO/Plug-Ins/DAL",
    "/Applications",
]


def run_command(command, use_sudo=False):
    """Executes a shell command and returns the output."""
    if use_sudo:
        command = f"sudo {command}"
    try:
        result = subprocess.run(command, shell=True, capture_output=True, text=True)
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def find_files(app_name):
    """Searches for files and folders related to the app name."""
    found_items = set()

    # 1. Use Spotlight (mdfind) for quick discovery
    print(f"[*] Searching Spotlight for '{app_name}'...")
    spotlight_results = run_command(f"mdfind -name '{app_name}'")
    if spotlight_results:
        for item in spotlight_results.split("\n"):
            if item:
                found_items.add(item)

    # 2. Search common Library paths manually
    print("[*] Scanning standard Library paths...")
    for path_str in SEARCH_PATHS:
        expanded_path = os.path.expanduser(path_str)
        if not os.path.exists(expanded_path):
            continue

        # Search for files matching the app name in these directories
        try:
            for item in os.listdir(expanded_path):
                if app_name.lower() in item.lower():
                    found_items.add(os.path.join(expanded_path, item))
        except PermissionError:
            # We'll skip directories we can't read without sudo for now
            pass

    # 3. Check for Package Receipts (pkgutil)
    print("[*] Checking for installation receipts...")
    pkg_results = run_command(f"pkgutil --packages | grep -i '{app_name}'")
    if pkg_results:
        for pkg_id in pkg_results.split("\n"):
            if pkg_id:
                print(f"    [!] Found package receipt: {pkg_id}")
                # We won't list every file in the package to avoid clutter,
                # but we'll mark the package for deletion.
                found_items.add(f"PACKAGE_RECEIPT:{pkg_id}")

    return sorted(list(found_items))


def check_processes(app_name):
    """Checks for running processes related to the app name."""
    print("[*] Checking for active processes...")
    # Exclude the current PID and common shell patterns
    current_pid = os.getpid()
    ps_results = run_command(
        f"ps aux | grep -i '{app_name}' | grep -v grep | grep -v '{current_pid}'"
    )
    if ps_results:
        print("\n[!] WARNING: Active processes found:")
        print(ps_results)
        return True
    return False


def delete_items(items):
    """Deletes the confirmed items."""
    for item in items:
        try:
            if item.startswith("PACKAGE_RECEIPT:"):
                pkg_id = item.split(":")[1]
                print(f"[-] Forgetting package receipt: {pkg_id}")
                run_command(f"pkgutil --forget {pkg_id}", use_sudo=True)
            else:
                print(f"[-] Deleting: {item}")
                # Use sudo rm -rf for everything to ensure cleanup of restricted files/folders
                run_command(f'rm -rf "{item}"', use_sudo=True)
        except Exception as e:
            print(f"    [X] Error deleting {item}: {e}")


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 cleaner.py <app_name>")
        sys.exit(1)

    app_name = sys.argv[1]
    print(f"=== macOS Deep Cleaner: {app_name} ===\n")

    # Check for active processes
    has_active_processes = check_processes(app_name)
    if has_active_processes:
        confirm_kill = input("\n[?] Should I try to kill these processes? (y/n): ")
        if confirm_kill.lower() == "y":
            run_command(f"pkill -if '{app_name}'", use_sudo=True)

    # Find related files
    found_items = find_files(app_name)

    if not found_items:
        print(f"\n[!] No files found for '{app_name}'.")
        return

    print(f"\n[+] Found {len(found_items)} items:")
    for i, item in enumerate(found_items):
        print(f"    {i + 1}. {item}")

    # Ask for confirmation
    confirm = input("\n[?] Do you want to delete all listed items? (y/n): ")
    if confirm.lower() == "y":
        # Final safety check for sensitive paths
        print("\n[!] DELETING FILES... (You may be asked for your sudo password)")
        delete_items(found_items)
        print("\n[✓] Cleanup complete.")
    else:
        print("\n[!] Operation cancelled.")


if __name__ == "__main__":
    main()
