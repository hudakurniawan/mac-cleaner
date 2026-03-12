import os
import sys
import subprocess
import re
import curses

# Version
VERSION = "1.2.2"

# Categories mapping for better UX
CATEGORY_MAP = {
    "Applications": ["/Applications", "/System/Applications", "~/Applications"],
    "Preferences": ["/Library/Preferences", "~/Library/Preferences"],
    "Application Support": [
        "/Library/Application Support",
        "~/Library/Application Support",
    ],
    "Caches & Logs": [
        "/Library/Caches",
        "~/Library/Caches",
        "/Library/Logs",
        "~/Library/Logs",
    ],
    "Containers & State": [
        "~/Library/Containers",
        "~/Library/Group Containers",
        "~/Library/Saved Application State",
    ],
    "System Components": [
        "/Library/LaunchAgents",
        "/Library/LaunchDaemons",
        "/Library/PrivilegedHelperTools",
        "/Library/Audio/Plug-Ins",
        "/Library/CoreMediaIO/Plug-Ins",
    ],
}

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


def get_category_name(path):
    """Determines the category of a given path."""
    for cat, prefixes in CATEGORY_MAP.items():
        for prefix in prefixes:
            expanded = os.path.expanduser(prefix)
            if path.startswith(expanded):
                return cat
    return "Other"


def is_precise_match(path, search_terms):
    """Checks if any search term matches precisely in the path."""
    path_lower = path.lower()
    for term in search_terms:
        # Use regex to find term as a whole word or surrounded by common separators
        # Includes / for path boundaries and \s for multi-word app names
        pattern = rf"(^|[._\-\s/]){re.escape(term)}([._\-\s/]|$)"
        if re.search(pattern, path_lower):
            return True
    return False


def find_files(app_name):
    """Searches and groups files into categories."""
    grouped_items = {cat: set() for cat in CATEGORY_MAP.keys()}
    grouped_items["Other"] = set()
    grouped_items["Package Receipts"] = set()

    # 1. Expand search terms (App Name + Bundle ID)
    search_terms = {app_name.lower()}

    # Add variation without spaces (e.g., 'FaithAlliances' for 'Faith Alliances')
    if " " in app_name:
        search_terms.add(app_name.lower().replace(" ", ""))

    # Try to find the bundle ID of the app
    app_paths = run_command(f"mdfind 'kind:app {app_name}'").split("\n")
    for app_path in app_paths:
        if (
            app_path
            and os.path.exists(app_path)
            and app_name.lower() in os.path.basename(app_path).lower()
        ):
            bid = run_command(f'mdls -name kMDItemCFBundleIdentifier -raw "{app_path}"')
            if bid and "(null)" not in bid:
                search_terms.add(bid.lower())
                # Add descriptive parts of bundle ID (e.g., 'wireguard' from 'com.wireguard.macos')
                for part in bid.split("."):
                    if len(part) > 3 and part.lower() not in [
                        "com",
                        "apple",
                        "macos",
                        "iosmac",
                        "apps",
                    ]:
                        search_terms.add(part.lower())

    # 2. Spotlight Search (Powerful discovery)
    print("[*] Searching Spotlight for related files...")
    for term in search_terms:
        # Use more targeted mdfind -name query
        spotlight_results = run_command(f'mdfind -name "{term}"')
        if spotlight_results:
            for item in spotlight_results.split("\n"):
                if item:
                    # Ignore common noise directories
                    if any(
                        x in item
                        for x in [
                            "/Extensions/",
                            "/BrowserMetrics/",
                            "/Service Worker/",
                        ]
                    ):
                        continue

                    if is_precise_match(item, search_terms):
                        if any(
                            os.path.expanduser(p) in item for p in SEARCH_PATHS
                        ) or item.endswith(".app"):
                            cat = get_category_name(item)
                            grouped_items[cat].add(item)

    # 3. Manual Deep Scan (Catch things Spotlight misses)
    print("[*] Scanning standard Library paths...")
    for path_str in SEARCH_PATHS:
        expanded_path = os.path.expanduser(path_str)
        if not os.path.exists(expanded_path):
            continue

        try:
            # Recursive search
            is_container_path = any(
                x in path_str for x in ["Containers", "Group Containers"]
            )
            max_depth = 10 if is_container_path else 2

            for root, dirs, files in os.walk(expanded_path):
                depth = root.count(os.sep) - expanded_path.count(os.sep)
                if depth > max_depth:
                    continue

                # Check directories
                for d in dirs:
                    if is_precise_match(d, search_terms):
                        full_path = os.path.join(root, d)
                        # Ignore noise
                        if any(
                            x in full_path for x in ["/Extensions/", "/BrowserMetrics/"]
                        ):
                            continue
                        cat = get_category_name(full_path)
                        grouped_items[cat].add(full_path)

                # Check files (for .plist etc)
                for f in files:
                    if is_precise_match(f, search_terms):
                        full_path = os.path.join(root, f)
                        # Ignore noise
                        if any(
                            x in full_path for x in ["/Extensions/", "/BrowserMetrics/"]
                        ):
                            continue
                        cat = get_category_name(full_path)
                        grouped_items[cat].add(full_path)
        except PermissionError:
            pass

    # 3. Package Receipts
    print("[*] Checking for installation receipts...")
    pkg_results = run_command(f"pkgutil --packages | grep -i '{app_name}'")
    if pkg_results:
        for pkg_id in pkg_results.split("\n"):
            if pkg_id:
                grouped_items["Package Receipts"].add(f"PACKAGE_RECEIPT:{pkg_id}")

    # Remove empty categories
    return {k: sorted(list(v)) for k, v in grouped_items.items() if v}


def check_processes(app_name):
    """Checks for running processes related to the app name."""
    print("[*] Checking for active processes...")
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
                run_command(f'rm -rf "{item}"', use_sudo=True)
        except Exception as e:
            print(f"    [X] Error deleting {item}: {e}")


def get_apps():
    """Gets list of apps from standard application folders."""
    apps = set()
    dirs = ["/Applications", "/System/Applications", "~/Applications"]
    for d in dirs:
        expanded = os.path.expanduser(d)
        if os.path.exists(expanded):
            for item in os.listdir(expanded):
                if item.endswith(".app"):
                    apps.add(item.replace(".app", ""))
    return sorted(list(apps))


def app_selector(stdscr, apps):
    """Interactive curses selector for apps."""
    # Set up colors
    curses.curs_set(0)  # Hide cursor
    curses.init_pair(1, curses.COLOR_BLACK, curses.COLOR_CYAN)  # Highlight color

    current_row = 0
    while True:
        stdscr.clear()
        h, w = stdscr.getmaxyx()

        title = (
            "=== Select an App to Clean (Use Arrows, Enter to Select, 'q' to Quit) ==="
        )
        stdscr.addstr(0, 0, title[: w - 1], curses.A_BOLD)

        # Display only what fits on the screen
        visible_rows = h - 2
        offset = max(0, current_row - visible_rows // 2)

        for i in range(visible_rows):
            idx = offset + i
            if idx >= len(apps):
                break

            y = i + 1
            text = f"  {apps[idx]}"

            if idx == current_row:
                stdscr.attron(curses.color_pair(1))
                stdscr.addstr(y, 0, text.ljust(w - 1)[: w - 1])
                stdscr.attroff(curses.color_pair(1))
            else:
                stdscr.addstr(y, 0, text[: w - 1])

        stdscr.refresh()
        key = stdscr.getch()

        if key == curses.KEY_UP and current_row > 0:
            current_row -= 1
        elif key == curses.KEY_DOWN and current_row < len(apps) - 1:
            current_row += 1
        elif key == ord("\n") or key == curses.KEY_ENTER:
            return apps[current_row]
        elif key == ord("q"):
            return None


def main():
    if len(sys.argv) < 2:
        apps = get_apps()
        if not apps:
            print("[!] No applications found in standard locations.")
            sys.exit(1)

        try:
            app_name = curses.wrapper(app_selector, apps)
            if not app_name:
                print("\n[!] Selection cancelled.")
                sys.exit(0)
        except curses.error:
            print(
                "[!] Could not initialize interactive selector (unsupported terminal)."
            )
            print("Usage: python3 cleaner.py <app_name>")
            sys.exit(1)
    elif sys.argv[1] in ["--help", "-h"]:
        print("Usage: python3 cleaner.py [app_name]")
        print("\nIf [app_name] is omitted, an interactive selector will appear.")
        print("\nOptions:")
        print("  -h, --help     Show this help message")
        print("  --version      Show version information")
        sys.exit(0)
    elif sys.argv[1] == "--version":
        print(f"macOS Deep Cleaner v{VERSION}")
        sys.exit(0)
    else:
        app_name = sys.argv[1]

    if len(app_name) < 3:
        print(f"[!] WARNING: '{app_name}' is a very short search term.")
        print(
            "[!] This might lead to many false positives. Consider a more specific name."
        )
        confirm = input("[?] Continue anyway? (y/n): ")
        if confirm.lower() != "y":
            sys.exit(0)

    print(f"=== macOS Deep Cleaner: {app_name} ===\n")

    if check_processes(app_name):
        confirm_kill = input("\n[?] Should I try to kill these processes? (y/n): ")
        if confirm_kill.lower() == "y":
            run_command(f"pkill -if '{app_name}'", use_sudo=True)

    while True:
        grouped_files = find_files(app_name)
        if not grouped_files:
            print(f"\n[✓] No remaining files found for '{app_name}'.")
            return

        while True:
            print("\n[+] Found items grouped by category:")
            categories = list(grouped_files.keys())
            for i, cat in enumerate(categories):
                count = len(grouped_files[cat])
                print(f"    {i + 1}. {cat} ({count} items)")

            print("\nOptions:")
            print("  'y' or 'a'   : Delete ALL items listed above")
            print("  'n'          : Finish / Exit")
            print("  '1,3'        : Delete specific categories (e.g., 1 and 3 only)")
            print("  'view 1'     : View detailed list of files in category 1")

            choice = input("\n[?] Your choice: ").strip().lower()

            to_delete = []

            if choice in ["y", "a"]:
                for cat_files in grouped_files.values():
                    to_delete.extend(cat_files)
                if to_delete:
                    print(
                        f"\n[!] Deleting {len(to_delete)} items... (Sudo password may be required)"
                    )
                    delete_items(to_delete)
                return  # Exit after deleting all
            elif choice.startswith("view "):
                try:
                    idx = int(choice.split(" ")[1]) - 1
                    cat = categories[idx]
                    print(f"\n--- Detail: {cat} ---")
                    for item in grouped_files[cat]:
                        print(f"  - {item}")
                    input("\nPress Enter to return to menu...")
                    continue
                except (IndexError, ValueError):
                    print("[!] Invalid category selection.")
                    continue
            elif "," in choice or choice.isdigit():
                try:
                    indices = [int(x.strip()) - 1 for x in choice.split(",")]
                    for idx in indices:
                        cat = categories[idx]
                        to_delete.extend(grouped_files[cat])

                    if to_delete:
                        print(
                            f"\n[!] Deleting {len(to_delete)} items from selected categories..."
                        )
                        delete_items(to_delete)
                        print("\n[✓] Selected categories cleaned.")
                        break  # Break inner loop to re-scan
                except (IndexError, ValueError):
                    print("[!] Invalid category selection.")
                    continue
            elif choice == "n":
                print("\n[!] Exiting.")
                return
            else:
                print("\n[!] Invalid input. Use 'y', 'n', 'view #', or '1,2'.")
                continue


if __name__ == "__main__":
    main()
