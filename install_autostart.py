"""Add/remove Nova from Windows startup.

    python install_autostart.py          → starts with Windows (tray mode)
    python install_autostart.py remove   → removes it again
"""
import sys
from pathlib import Path

import win32com.client

STARTUP = Path.home() / "AppData/Roaming/Microsoft/Windows/Start Menu/Programs/Startup"
SHORTCUT = STARTUP / "Nova.lnk"
HERE = Path(__file__).parent


def install():
    pythonw = Path(sys.executable).parent / "pythonw.exe"
    shell = win32com.client.Dispatch("WScript.Shell")
    sc = shell.CreateShortCut(str(SHORTCUT))
    sc.TargetPath = str(pythonw)
    sc.Arguments = f'"{HERE / "nova_tray.py"}"'
    sc.WorkingDirectory = str(HERE)
    sc.Description = "Nova voice assistant"
    sc.save()
    print(f"Installed: Nova will start with Windows.\n  {SHORTCUT}")


def remove():
    if SHORTCUT.exists():
        SHORTCUT.unlink()
        print("Removed: Nova no longer starts with Windows.")
    else:
        print("Nothing to remove — autostart wasn't installed.")


if __name__ == "__main__":
    remove() if "remove" in sys.argv else install()
