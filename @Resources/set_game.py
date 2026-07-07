"""
Opens a file picker for a game's .exe or shortcut (.lnk), extracts its
icon and a display title, and writes them to game_info.json / game_icon.png
for the Playing skin to show. Triggered by clicking the game icon/title
in Playing.ini.
"""

import json
import subprocess
import tkinter as tk
from pathlib import Path
from tkinter import filedialog

RESOURCES_DIR = Path(__file__).parent
INFO_FILE = RESOURCES_DIR / "game_info.json"
ICON_FILE = RESOURCES_DIR / "game_icon.png"


def run_powershell(script):
    result = subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        text=True,
        timeout=15,
    )
    return result.stdout.strip()


def resolve_shortcut(lnk_path):
    script = (
        f"$s = (New-Object -COM WScript.Shell).CreateShortcut('{lnk_path}'); "
        "Write-Output $s.TargetPath"
    )
    target = run_powershell(script)
    return target if target else lnk_path


def get_exe_title(exe_path, fallback):
    script = (
        f"$vi = (Get-Item -LiteralPath '{exe_path}').VersionInfo; "
        "if ($vi.ProductName) { Write-Output $vi.ProductName } "
        "elseif ($vi.FileDescription) { Write-Output $vi.FileDescription }"
    )
    title = run_powershell(script)
    return title if title else fallback


def extract_icon(exe_path):
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$icon = [System.Drawing.Icon]::ExtractAssociatedIcon('{exe_path}'); "
        f"$icon.ToBitmap().Save('{ICON_FILE}', [System.Drawing.Imaging.ImageFormat]::Png)"
    )
    run_powershell(script)


def main():
    root = tk.Tk()
    root.withdraw()
    picked = filedialog.askopenfilename(
        title="Choose the game's .exe or shortcut",
        filetypes=[("Executable or shortcut", "*.exe *.lnk")],
    )
    root.destroy()

    if not picked:
        print("No file selected")
        return

    picked_path = Path(picked)
    if picked_path.suffix.lower() == ".lnk":
        target_path = resolve_shortcut(str(picked_path))
        title = picked_path.stem
    else:
        target_path = str(picked_path)
        title = get_exe_title(target_path, picked_path.stem)

    extract_icon(target_path)

    with open(INFO_FILE, "w", encoding="utf-8") as f:
        json.dump({"GameTitle": title}, f, indent=2)

    print(f"Set game to '{title}' ({target_path})")


if __name__ == "__main__":
    main()
