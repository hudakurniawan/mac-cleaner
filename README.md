# macOS Deep Cleaner

A simple Python tool to help you find and delete all hidden files, caches, and system-level components of uninstalled apps.

## How to use
1.  Open your terminal.
2.  Run the cleaner by passing the name of the app you want to clean:
    ```bash
    python3 cleaner.py "AppName"
    ```
    *(e.g., `python3 cleaner.py "Spotify"`)**

## Features
- **Spotlight Search**: Uses macOS `mdfind` to quickly locate files.
- **Deep Scan**: Manually scans `/Library` and `~/Library` directories.
- **Process Check**: Detects if any background processes related to the app are still running.
- **Receipt Removal**: Cleans up installation records from `pkgutil`.
- **Safety First**: Lists everything and asks for confirmation before deleting.

## Requirements
- macOS (tested on Sonoma)
- Python 3.x
- `sudo` access (to remove system-level files)

---

## Credits & Disclaimer
> **Note:** This tool's initial logic and safety checks were drafted with the assistance of AI (Gemini CLI). While it has been tested for safety, always review the list of files found before confirming deletion.
