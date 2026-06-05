"""Nova — system tray launcher.

Run with no console window:   pythonw nova_tray.py
Nova runs as a hidden background process; the tray icon (purple N) lets
you restart or quit it. Output goes to nova.log next to the code.
"""
import socket
import subprocess
import sys
from pathlib import Path

import pystray
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).parent
LOG = HERE / "nova.log"

# single-instance lock for the tray itself
_tray_lock = socket.socket()
try:
    _tray_lock.bind(("127.0.0.1", 52790))
except OSError:
    sys.exit(0)  # tray already running

_proc: subprocess.Popen | None = None


def _make_icon() -> Image.Image:
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.ellipse((2, 2, 62, 62), fill=(98, 0, 234))          # purple circle
    try:
        font = ImageFont.truetype("arialbd.ttf", 36)
    except OSError:
        font = ImageFont.load_default()
    d.text((32, 30), "N", font=font, fill="white", anchor="mm")
    return img


def _start_nova():
    global _proc
    log = open(LOG, "a", encoding="utf-8", errors="replace")
    _proc = subprocess.Popen(
        [sys.executable, str(HERE / "main.py")],
        cwd=str(HERE),
        stdout=log, stderr=subprocess.STDOUT,
        creationflags=subprocess.CREATE_NO_WINDOW,
    )


def _stop_nova():
    global _proc
    if _proc and _proc.poll() is None:
        _proc.terminate()
    _proc = None


def _status(icon):
    running = _proc is not None and _proc.poll() is None
    return f"Nova — {'listening' if running else 'stopped'}"


def on_restart(icon, item):
    _stop_nova()
    _start_nova()


def on_quit(icon, item):
    _stop_nova()
    icon.stop()


def main():
    _start_nova()
    icon = pystray.Icon(
        "nova", _make_icon(), "Nova voice assistant",
        menu=pystray.Menu(
            pystray.MenuItem(lambda item: _status(None), None, enabled=False),
            pystray.MenuItem("Restart Nova", on_restart),
            pystray.MenuItem("Quit", on_quit),
        ),
    )
    icon.run()


if __name__ == "__main__":
    main()
