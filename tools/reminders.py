"""Nova — reminders & timers.

Fire while Nova is running: a chime + spoken message from a background
thread (with its own COM/SAPI instance, since the main one isn't
thread-safe). Reminders don't survive a restart — keep Nova running.
"""
import threading
import winsound

import pythoncom
import win32com.client


_active: list[str] = []   # human-readable list of pending reminders


def _fire(message: str):
    if message in _active:
        _active.remove(message)
    pythoncom.CoInitialize()
    try:
        for _ in range(3):
            winsound.Beep(1000, 200)
        voice = win32com.client.Dispatch("SAPI.SpVoice")
        # use the same fallback voice as the main speaker (consistency)
        import config
        voices = voice.GetVoices()
        if config.TTS_VOICE_INDEX < voices.Count:
            voice.Voice = voices.Item(config.TTS_VOICE_INDEX)
        voice.Speak(f"Reminder: {message}")
    finally:
        pythoncom.CoUninitialize()


def _schedule(seconds: float, message: str):
    t = threading.Timer(seconds, _fire, args=(message,))
    t.daemon = True
    t.start()
    _active.append(message)


def set_reminder(minutes: float = 0, seconds: float = 0,
                 hours: float = 0, message: str = "you asked me to remind you") -> str:
    total = hours * 3600 + minutes * 60 + seconds
    if total <= 0:
        return "I need to know when — say something like 'remind me in 10 minutes to check the oven'."
    _schedule(total, message)
    if hours:
        when = f"{hours:g} hour{'s' if hours != 1 else ''}"
    elif minutes:
        when = f"{minutes:g} minute{'s' if minutes != 1 else ''}"
    else:
        when = f"{seconds:g} seconds"
    return f"Got it — I'll remind you in {when}: {message}."


def set_timer(minutes: float = 0, seconds: float = 0) -> str:
    total = minutes * 60 + seconds
    if total <= 0:
        return "How long should the timer be?"
    _schedule(total, "your timer is done")
    when = f"{minutes:g} minute{'s' if minutes != 1 else ''}" if minutes else f"{seconds:g} seconds"
    return f"Timer set for {when}."


def list_reminders() -> str:
    if not _active:
        return "You have no pending reminders."
    return f"You have {len(_active)} pending: {'; '.join(_active)}."
