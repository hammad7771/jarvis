"""Nova — fast rule-based intent matching.

Clear commands (time, play, create...) are routed here BEFORE the LLM:
deterministic, instant, and immune to the small model's chat-drift.
Anything that doesn't match falls through to the brain.
"""
import re

import config

# spoken names of folders we can extract ("...in my downloads")
_FOLDERS = "|".join(config.KNOWN_FOLDERS)

_SITES = {
    "youtube": "youtube.com",
    "google": "google.com",
    "gmail": "gmail.com",
    "facebook": "facebook.com",
    "instagram": "instagram.com",
    "twitter": "twitter.com",
    "github": "github.com",
    "chatgpt": "chatgpt.com",
}

_APPS = ("notepad", "calculator", "paint", "explorer", "file explorer",
         "task manager", "command prompt", "settings")


def _split_folder(text: str) -> tuple[str, str | None]:
    """Strip a trailing 'on/in/from (my) <folder>' and return (rest, folder)."""
    m = re.search(rf"\s+(?:on|in|from|to)\s+(?:my\s+)?(?:the\s+)?({_FOLDERS})\s*$", text)
    if m:
        return text[:m.start()].strip(), m.group(1)
    return text.strip(), None


def parse(text: str) -> tuple[str, dict] | None:
    """Return (action, args) for a clear command, else None (→ ask the LLM)."""
    t = text.lower().strip()
    # Whisper adds punctuation ("Create a folder, called test.") — strip it,
    # but keep inner dots so "open youtube.com" still works
    t = t.replace(",", "").replace("!", "").replace("?", "").rstrip(".").strip()

    # time & date
    if re.search(r"\b(?:what(?:'s| is)?\s+(?:the\s+)?time|time is it)\b", t):
        return "get_time", {}
    if re.search(r"\b(?:what(?:'s| is)?\s+(?:the\s+)?(?:date|day)|today'?s date)\b", t):
        return "get_date", {}

    # music — "play despacito"
    m = re.search(r"\bplay\s+(?:some\s+)?(.+)", t)
    if m:
        return "play_song", {"query": m.group(1).strip()}

    # maps — "open maps to lahore", "directions to airport"
    m = re.search(r"\b(?:maps?|directions?|navigate)\s*(?:to|for|of)?\s+(.+)", t)
    if m:
        return "open_maps", {"query": m.group(1).strip()}

    # create folder / file
    m = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?folder\s*(?:called|named)?\s+(.+)", t)
    if m:
        name, folder = _split_folder(m.group(1))
        return "create_folder", {"name": name, "folder": folder}
    m = re.search(r"\b(?:create|make|new)\s+(?:a\s+)?file\s*(?:called|named)?\s+(.+)", t)
    if m:
        name, folder = _split_folder(m.group(1))
        return "create_file", {"name": name, "folder": folder}

    # delete — "delete old notes from downloads"
    m = re.search(r"\b(?:delete|remove|trash)\s+(?:the\s+)?(?:file\s+|folder\s+)?(.+)", t)
    if m:
        name, folder = _split_folder(m.group(1))
        return "delete_file", {"name": name, "folder": folder}

    # list files — "what's on my desktop", "list files in downloads",
    # "how many items are there on desktop"
    m = re.search(rf"\b(?:list|show)\s+(?:the\s+)?files?\s*(?:on|in)?\s*(?:my\s+)?({_FOLDERS})?", t)
    if m:
        return "list_files", {"folder": m.group(1)}
    m = re.search(rf"\bwhat(?:'s| is)\s+(?:on|in)\s+my\s+({_FOLDERS})\b", t)
    if m:
        return "list_files", {"folder": m.group(1)}
    m = re.search(rf"\bhow\s+many\s+(?:items?|files?|things?).*?(?:on|in)\s+(?:my\s+|the\s+)?({_FOLDERS})\b", t)
    if m:
        return "list_files", {"folder": m.group(1)}

    # memory — "remember that my exam is on friday", "what do you remember"
    if re.search(r"\bwhat do you (?:know|remember)\b", t):
        return "recall", {}
    m = re.search(r"\bremember\s+(?:that\s+)?(.+)", t)
    if m and "remind me" not in t:
        return "remember", {"fact": m.group(1).strip()}
    m = re.search(r"\bforget\s+(?:about\s+|that\s+|everything about\s+)?(.+)", t)
    if m:
        return "forget", {"keyword": m.group(1).strip()}

    # reminders & timers — "remind me in 20 minutes to check the oven",
    # "remind me to call ali in 2 hours", "set a timer for 5 minutes"
    m = re.search(r"\bremind me\s+in\s+(\d+(?:\.\d+)?)\s+(second|minute|hour)s?\s*(?:to|that|about)?\s*(.*)", t)
    if m:
        amount, unit, msg = float(m.group(1)), m.group(2), m.group(3).strip()
        return "set_reminder", {unit + "s": amount, "message": msg or "you asked me to remind you"}
    m = re.search(r"\bremind me\s+(?:to|that|about)\s+(.+?)\s+in\s+(\d+(?:\.\d+)?)\s+(second|minute|hour)s?\b", t)
    if m:
        msg, amount, unit = m.group(1).strip(), float(m.group(2)), m.group(3)
        return "set_reminder", {unit + "s": amount, "message": msg}
    m = re.search(r"\b(?:set\s+)?(?:a\s+)?timer\s+(?:for\s+)?(\d+(?:\.\d+)?)\s+(second|minute)s?\b", t)
    if m:
        return "set_timer", {m.group(2) + "s": float(m.group(1))}
    if re.search(r"\b(?:list|any|what|show)\b.*\breminders?\b|\breminders\b\s*$", t):
        return "list_reminders", {}

    # window control — "minimize this window", "show desktop"...
    if re.search(r"\bminimi[sz]e\s+(?:this\s+|the\s+)?window\b", t):
        return "minimize_window", {}
    if re.search(r"\bmaximi[sz]e\s+(?:this\s+|the\s+)?window\b", t):
        return "maximize_window", {}
    if re.search(r"\bclose\s+(?:this\s+|the\s+)?window\b", t):
        return "close_window", {}
    if re.search(r"\b(?:switch|next)\s+window\b", t):
        return "switch_window", {}
    if re.search(r"\bshow\s+(?:the\s+|my\s+)?desktop\b|\bminimi[sz]e\s+(?:everything|all)\b", t):
        return "show_desktop", {}

    # Windows settings — dark mode + settings pages
    if re.search(r"\b(?:turn on|enable|switch to)\s+dark mode\b|\bdark mode on\b", t):
        return "set_dark_mode", {"on": True}
    if re.search(r"\b(?:turn off|disable)\s+dark mode\b|\b(?:turn on|enable|switch to)\s+light mode\b|\bdark mode off\b", t):
        return "set_dark_mode", {"on": False}
    m = re.search(r"\bopen\s+(.+?)\s+settings\b|\b(.+?)\s+settings\s*$", t)
    if m:
        page = (m.group(1) or m.group(2) or "").strip()
        return "open_settings", {"page": page}

    # volume / brightness / power / screenshot / lock
    m = re.search(r"\b(?:set\s+)?volume\s+(?:to\s+)?(\d{1,3})\s*(?:percent)?\b", t)
    if m:
        return "set_volume", {"level": int(m.group(1))}
    if re.search(r"\b(?:volume|sound)\s+(?:up|increase|louder|raise)|\b(?:increase|raise|turn up)\s+(?:the\s+)?(?:volume|sound)|\bmake it louder\b", t):
        return "volume_up", {}
    if re.search(r"\b(?:volume|sound)\s+(?:down|decrease|lower|reduce)|\b(?:decrease|lower|reduce|turn down)\s+(?:the\s+)?(?:volume|sound)", t):
        return "volume_down", {}
    if re.search(r"\b(?:mute|unmute|silence)\b", t):
        return "mute", {}
    m = re.search(r"\bbrightness\s+(?:to\s+)?(\d{1,3})|\bset\s+brightness\s+(?:to\s+)?(\d{1,3})", t)
    if m:
        return "set_brightness", {"level": int(m.group(1) or m.group(2))}
    if re.search(r"\block\s+(?:the\s+|my\s+)?(?:pc|computer|screen|system)\b", t):
        return "lock_pc", {}
    if re.search(r"\b(?:take\s+(?:a\s+)?)?screen\s*shot\b", t):
        return "take_screenshot", {}
    if re.search(r"\bcancel\s+(?:the\s+)?(?:shutdown|shut down|restart)\b", t):
        return "cancel_shutdown", {}
    m = re.search(r"\b(?:shut\s*down|turn off)\s+(?:the\s+|my\s+)?(?:pc|computer|system)?(?:\s+in\s+(\d+)\s+minutes?)?", t)
    if m and re.search(r"\b(?:pc|computer|system|shut\s*down)\b", t):
        return "shutdown_pc", {"minutes": int(m.group(1) or 0)}
    m = re.search(r"\brestart\s+(?:the\s+|my\s+)?(?:pc|computer|system)(?:\s+in\s+(\d+)\s+minutes?)?", t)
    if m:
        return "restart_pc", {"minutes": int(m.group(1) or 0)}

    # open app / website
    m = re.search(r"\b(?:open|launch|start)\s+(.+)", t)
    if m:
        target = m.group(1).strip()
        for app in _APPS:
            if app in target:
                return "open_app", {"name": app}
        for site, url in _SITES.items():
            if site in target:
                return "open_website", {"url": url}
        if "." in target:  # spoken/heard as a domain
            return "open_website", {"url": target.replace(" ", "")}
        # anything else → the universal app launcher resolves it
        return "open_app", {"name": target}

    # web search — "search how to learn python", "google weather lahore"
    m = re.search(r"\b(?:search|google|look up)\s+(?:for\s+)?(.+)", t)
    if m:
        return "search_web", {"query": m.group(1).strip()}

    return None  # not a clear command → let the LLM handle it


if __name__ == "__main__":
    tests = [
        "what time is it",
        "play shape of you",
        "create a folder called school work on my desktop",
        "delete old resume from downloads",
        "open calculator",
        "open youtube",
        "search how to learn python",
        "navigate to the nearest coffee shop",
        "i'm feeling tired today",       # → None (chat → LLM)
        "tell me a joke",                # → None (chat → LLM)
    ]
    for s in tests:
        print(f"{s!r:55} -> {parse(s)}")
