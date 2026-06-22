import os
import re
import subprocess

# Generic terms to ignore when extracting from bundle IDs
BLACKLIST_TERMS = [
    "com", "apple", "macos", "iosmac", "apps", "helper", "service", 
    "agent", "extension", "plugin", "mobile", "desktop", "framework", 
    "backend", "frontend",
]

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
    "/Applications",
]

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

def get_category_name(path):
    for cat, prefixes in CATEGORY_MAP.items():
        for prefix in prefixes:
            expanded = os.path.expanduser(prefix)
            if path.startswith(expanded):
                return cat
    return "Other"

def is_precise_match(path, search_terms):
    path_lower = path.lower()

    # CRITICAL SAFETY: Never match files in personal data or cloud storage folders
    ignored_patterns = [
        "/onedrive", "/dropbox", "/google drive", "/icloud",
        "/documents/", "/desktop/", "/downloads/", "/pictures/",
    ]
    if any(pattern in path_lower for pattern in ignored_patterns):
        return False

    for term in search_terms:
        pattern = rf"(^|[._\-\s/]){re.escape(term)}([._\-\s/]|$)"
        if re.search(pattern, path_lower):
            lib_roots = [
                "library/application support", "library/preferences",
                "library/caches", "library/containers",
            ]
            is_in_lib_root = False
            for root in lib_roots:
                if root in path_lower:
                    is_in_lib_root = True
                    parts = path_lower.split("/")
                    root_parts = root.split("/")
                    last_root_part = root_parts[-1]

                    if last_root_part in parts:
                        root_idx = parts.index(last_root_part)
                        if len(parts) > root_idx + 1 and parts[root_idx + 1] == term:
                            return True
                        if len(parts) > root_idx + 1:
                            continue
            if not is_in_lib_root:
                return True
    return False

def get_installed_apps():
    apps = set()
    dirs = ["/Applications", "/System/Applications", "~/Applications"]
    for d in dirs:
        expanded = os.path.expanduser(d)
        if os.path.exists(expanded):
            for item in os.listdir(expanded):
                if item.endswith(".app"):
                    apps.add(item.replace(".app", ""))
    return sorted(list(apps))

def find_app_files(app_name):
    grouped_items = {cat: set() for cat in CATEGORY_MAP.keys()}
    grouped_items["Other"] = set()
    grouped_items["Package Receipts"] = set()

    search_terms = {app_name.lower()}
    if " " in app_name:
        search_terms.add(app_name.lower().replace(" ", ""))

    app_paths = run_command(f"mdfind 'kind:app {app_name}'").split("\n")
    for app_path in app_paths:
        if app_path and os.path.exists(app_path) and app_name.lower() in os.path.basename(app_path).lower():
            bid = run_command(f'mdls -name kMDItemCFBundleIdentifier -raw "{app_path}"')
            if bid and "(null)" not in bid:
                search_terms.add(bid.lower())
                parts = bid.split(".")
                if len(parts) > 1:
                    tail = parts[-1].lower()
                    if len(tail) > 3 and tail not in BLACKLIST_TERMS:
                        search_terms.add(tail)

    for term in search_terms:
        spotlight_results = run_command(f'mdfind -name "{term}"')
        if spotlight_results:
            for item in spotlight_results.split("\n"):
                if item:
                    if any(x in item for x in ["/Extensions/", "/BrowserMetrics/", "/Service Worker/"]):
                        continue
                    if is_precise_match(item, search_terms):
                        if any(os.path.expanduser(p) in item for p in SEARCH_PATHS) or item.endswith(".app"):
                            cat = get_category_name(item)
                            grouped_items[cat].add(item)

    for path_str in SEARCH_PATHS:
        expanded_path = os.path.expanduser(path_str)
        if not os.path.exists(expanded_path):
            continue

        try:
            is_container_path = any(x in path_str for x in ["Containers", "Group Containers"])
            max_depth = 10 if is_container_path else 2

            for root, dirs, files in os.walk(expanded_path):
                depth = root.count(os.sep) - expanded_path.count(os.sep)
                if depth > max_depth:
                    continue

                for d in dirs:
                    if is_precise_match(d, search_terms):
                        full_path = os.path.join(root, d)
                        if any(x in full_path for x in ["/Extensions/", "/BrowserMetrics/"]):
                            continue
                        cat = get_category_name(full_path)
                        grouped_items[cat].add(full_path)

                for f in files:
                    if is_precise_match(f, search_terms):
                        full_path = os.path.join(root, f)
                        if any(x in full_path for x in ["/Extensions/", "/BrowserMetrics/"]):
                            continue
                        cat = get_category_name(full_path)
                        grouped_items[cat].add(full_path)
        except PermissionError:
            pass

    pkg_results = run_command(f"pkgutil --packages | grep -i '{app_name}'")
    if pkg_results:
        for pkg_id in pkg_results.split("\n"):
            if pkg_id:
                grouped_items["Package Receipts"].add(f"PACKAGE_RECEIPT:{pkg_id}")

    return {k: sorted(list(v)) for k, v in grouped_items.items() if v}
