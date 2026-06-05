"""Nova — file & folder operations.

Deletions go to the Recycle Bin (send2trash), never permanent.
Spoken names are resolved against Desktop / Downloads / Documents etc.
"""
from pathlib import Path

from send2trash import send2trash

import config


def _base_folder(folder: str | None) -> Path:
    """Map a spoken folder name ('desktop', 'downloads'...) to a real path."""
    if not folder:
        return config.DEFAULT_FOLDER
    return config.KNOWN_FOLDERS.get(folder.strip().lower(), config.DEFAULT_FOLDER)


def _resolve(name: str, folder: str | None = None) -> Path | None:
    """Find a file/folder from its spoken name. Tries exact, then
    case-insensitive, then ignores-extension matches."""
    p = Path(name)
    if p.is_absolute() and p.exists():
        return p
    base = _base_folder(folder)
    candidate = base / name
    if candidate.exists():
        return candidate
    low = name.lower().replace(" ", "")
    for item in base.iterdir():
        item_low = item.name.lower().replace(" ", "")
        if item_low == low or item.stem.lower().replace(" ", "") == low:
            return item
    return None


# ── tools ───────────────────────────────────────────────────

def create_folder(name: str, folder: str | None = None) -> str:
    target = _base_folder(folder) / name
    if target.exists():
        return f"A folder called {name} already exists there."
    target.mkdir(parents=True)
    return f"Created folder {name} on your {folder or 'desktop'}."


def create_file(name: str, folder: str | None = None, content: str = "") -> str:
    target = _base_folder(folder) / name
    if target.exists():
        return f"{name} already exists there."
    target.write_text(content, encoding="utf-8")
    return f"Created {name} on your {folder or 'desktop'}."


def delete_file(name: str, folder: str | None = None) -> str:
    target = _resolve(name, folder)
    if target is None:
        return f"I couldn't find {name} in your {folder or 'desktop'}."
    send2trash(str(target))
    return f"Done — {target.name} has been moved to the recycle bin."


def list_files(folder: str | None = None) -> str:
    base = _base_folder(folder)
    items = sorted(base.iterdir(), key=lambda p: p.name.lower())
    if not items:
        return f"Your {folder or 'desktop'} is empty."
    names = [i.name for i in items[:15]]
    extra = f" and {len(items) - 15} more" if len(items) > 15 else ""
    return f"Your {folder or 'desktop'} has: {', '.join(names)}{extra}."
