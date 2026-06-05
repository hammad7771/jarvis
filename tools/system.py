"""Nova — system actions: time, date, apps, volume, brightness, power."""
import ctypes
import datetime
import subprocess
from pathlib import Path

# Windows virtual key codes for the media volume keys
_VK_VOLUME_MUTE, _VK_VOLUME_DOWN, _VK_VOLUME_UP = 0xAD, 0xAE, 0xAF


def _press_key(vk: int, times: int = 1):
    for _ in range(times):
        ctypes.windll.user32.keybd_event(vk, 0, 0, 0)  # key down
        ctypes.windll.user32.keybd_event(vk, 0, 2, 0)  # key up

# Apps Nova is allowed to launch by spoken name
APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "paint": "mspaint.exe",
    "explorer": "explorer.exe",
    "file explorer": "explorer.exe",
    "task manager": "taskmgr.exe",
    "command prompt": "cmd.exe",
    "settings": "ms-settings:",
}


def get_time() -> str:
    now = datetime.datetime.now()
    return f"It's {now.strftime('%I:%M %p').lstrip('0')}."


def get_date() -> str:
    today = datetime.date.today()
    return f"Today is {today.strftime('%A, %B %d, %Y')}."


# ── window control ──────────────────────────────────────────

def minimize_window() -> str:
    import win32con
    import win32gui
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
    return "Minimized."


def maximize_window() -> str:
    import win32con
    import win32gui
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
    return "Maximized."


def close_window() -> str:
    import win32con
    import win32gui
    hwnd = win32gui.GetForegroundWindow()
    if hwnd:
        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
    return "Closed the window."


def switch_window() -> str:
    # simulate Alt+Tab
    ALT, TAB = 0x12, 0x09
    ctypes.windll.user32.keybd_event(ALT, 0, 0, 0)
    ctypes.windll.user32.keybd_event(TAB, 0, 0, 0)
    ctypes.windll.user32.keybd_event(TAB, 0, 2, 0)
    ctypes.windll.user32.keybd_event(ALT, 0, 2, 0)
    return "Switched."


def show_desktop() -> str:
    import win32com.client
    win32com.client.Dispatch("Shell.Application").MinimizeAll()
    return "Showing the desktop."


# ── Windows settings ────────────────────────────────────────

def set_dark_mode(on: bool = True) -> str:
    import winreg
    val = 0 if on else 1   # 0 = dark, 1 = light
    key = winreg.OpenKey(
        winreg.HKEY_CURRENT_USER,
        r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        0, winreg.KEY_SET_VALUE)
    winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
    winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
    winreg.CloseKey(key)
    return f"{'Dark' if on else 'Light'} mode on."


_SETTINGS_PAGES = {
    "wifi": "ms-settings:network-wifi",
    "wi-fi": "ms-settings:network-wifi",
    "bluetooth": "ms-settings:bluetooth",
    "night light": "ms-settings:nightlight",
    "display": "ms-settings:display",
    "sound": "ms-settings:sound",
    "battery": "ms-settings:batterysaver",
    "airplane": "ms-settings:network-airplanemode",
    "apps": "ms-settings:appsfeatures",
    "windows update": "ms-settings:windowsupdate",
    "privacy": "ms-settings:privacy",
}


def open_settings(page: str = "") -> str:
    uri = _SETTINGS_PAGES.get(page.strip().lower(), "ms-settings:")
    subprocess.Popen(["start", uri], shell=True)
    return f"Opening {page or 'Windows'} settings."


# ── volume ──────────────────────────────────────────────────

def set_volume(level: int) -> str:
    """Jump straight to an exact volume percentage (pycaw)."""
    level = max(0, min(100, int(level)))
    from pycaw.pycaw import AudioUtilities
    AudioUtilities.GetSpeakers().EndpointVolume.SetMasterVolumeLevelScalar(
        level / 100, None)
    return f"Volume set to {level} percent."


def volume_up(amount: int = 5) -> str:
    _press_key(_VK_VOLUME_UP, amount)        # each press = 2 volume steps
    return "Volume up."


def volume_down(amount: int = 5) -> str:
    _press_key(_VK_VOLUME_DOWN, amount)
    return "Volume down."


def mute() -> str:
    _press_key(_VK_VOLUME_MUTE)
    return "Toggled mute."


def set_brightness(level: int) -> str:
    level = max(0, min(100, int(level)))
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         f"(Get-WmiObject -Namespace root/WMI -Class WmiMonitorBrightnessMethods)"
         f".WmiSetBrightness(1,{level})"],
        capture_output=True, text=True,
    )
    if r.returncode != 0:
        return "Sorry, brightness control isn't supported on this display."
    return f"Brightness set to {level} percent."


def lock_pc() -> str:
    ctypes.windll.user32.LockWorkStation()
    return "Locking your PC."


def take_screenshot() -> str:
    from PIL import ImageGrab
    folder = Path.home() / "Pictures" / "Nova Screenshots"
    folder.mkdir(parents=True, exist_ok=True)
    stamp = datetime.datetime.now().strftime("%Y-%m-%d %H-%M-%S")
    path = folder / f"screenshot {stamp}.png"
    ImageGrab.grab().save(path)
    return f"Screenshot saved to your Pictures, Nova Screenshots folder."


def shutdown_pc(minutes: int = 0) -> str:
    subprocess.run(["shutdown", "/s", "/t", str(int(minutes) * 60)])
    when = "now" if not minutes else f"in {minutes} minutes"
    return f"Shutting down {when}. Say 'Nova cancel shutdown' to stop it."


def restart_pc(minutes: int = 0) -> str:
    subprocess.run(["shutdown", "/r", "/t", str(int(minutes) * 60)])
    when = "now" if not minutes else f"in {minutes} minutes"
    return f"Restarting {when}. Say 'Nova cancel shutdown' to stop it."


def cancel_shutdown() -> str:
    r = subprocess.run(["shutdown", "/a"], capture_output=True)
    if r.returncode != 0:
        return "There was no shutdown scheduled."
    return "Shutdown cancelled."


# ── universal app launcher ──────────────────────────────────
# Uses Windows Get-StartApps: covers classic AND Store/UWP apps.
_app_index: dict[str, str] | None = None  # display name → AppID

# spoken shorthand → real app names
_ALIASES = {
    "vs code": "visual studio code",
    "code": "visual studio code",
    "word": "word",          # prefer MS Word over WordPad when present
    "excel": "excel",
    "powerpoint": "powerpoint",
    "browser": "chrome",
}


def _norm(s: str) -> str:
    return "".join(c for c in s.lower() if c.isalnum())


def _build_app_index() -> dict[str, str]:
    import json as _json
    r = subprocess.run(
        ["powershell", "-NoProfile", "-Command",
         "[Console]::OutputEncoding=[Text.Encoding]::UTF8; "
         "Get-StartApps | ConvertTo-Json -Compress"],
        capture_output=True, timeout=30,
    )
    index: dict[str, str] = {}
    try:
        for item in _json.loads(r.stdout.decode("utf-8", errors="replace")):
            name = item["Name"].lower()
            # skip uninstallers, help files, updaters etc.
            if any(w in name for w in ("uninstall", "help", "readme", "update",
                                       "documentation", "manual", "website")):
                continue
            index[name] = item["AppID"]
    except (ValueError, KeyError, TypeError):
        pass
    return index


def _find_app(key: str, index: dict[str, str]) -> str | None:
    key = _ALIASES.get(key, key)
    nkey = _norm(key)
    by_norm = {_norm(k): k for k in index}
    if nkey in by_norm:
        return by_norm[nkey]
    starts = [k for n, k in by_norm.items() if n.startswith(nkey)]
    if starts:
        return min(starts, key=len)
    contains = [k for n, k in by_norm.items() if nkey in n]
    if contains:
        return min(contains, key=len)
    import difflib
    close = difflib.get_close_matches(nkey, by_norm.keys(), n=1, cutoff=0.75)
    return by_norm[close[0]] if close else None


def open_app(name: str) -> str:
    global _app_index
    key = name.strip().lower()

    # 1) curated built-ins (instant, exact)
    target = APPS.get(key)
    if target:
        if target.startswith("ms-settings"):
            subprocess.Popen(["start", target], shell=True)
        else:
            subprocess.Popen([target])
        return f"Opening {name}."

    # 2) anything installed (classic + Store apps via Get-StartApps)
    if _app_index is None:
        _app_index = _build_app_index()
    match = _find_app(key, _app_index)
    if match:
        subprocess.Popen(
            ["explorer.exe", f"shell:AppsFolder\\{_app_index[match]}"])
        return f"Opening {match}."
    return f"I couldn't find an app called {name}."
