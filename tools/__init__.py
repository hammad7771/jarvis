"""Nova — tool registry. Maps action names to functions."""
from tools import browser, files, memory, reminders, system

# Every tool returns a string that Nova speaks back to the user.
REGISTRY = {
    "create_folder": files.create_folder,
    "create_file":   files.create_file,
    "delete_file":   files.delete_file,
    "list_files":    files.list_files,
    "play_song":     browser.play_song,
    "open_maps":     browser.open_maps,
    "search_web":    browser.search_web,
    "open_website":  browser.open_website,
    "get_time":      system.get_time,
    "get_date":      system.get_date,
    "open_app":      system.open_app,
    "volume_up":     system.volume_up,
    "volume_down":   system.volume_down,
    "set_volume":    system.set_volume,
    "mute":          system.mute,
    "minimize_window": system.minimize_window,
    "maximize_window": system.maximize_window,
    "close_window":  system.close_window,
    "switch_window": system.switch_window,
    "show_desktop":  system.show_desktop,
    "set_dark_mode": system.set_dark_mode,
    "open_settings": system.open_settings,
    "set_brightness": system.set_brightness,
    "lock_pc":       system.lock_pc,
    "take_screenshot": system.take_screenshot,
    "shutdown_pc":   system.shutdown_pc,
    "restart_pc":    system.restart_pc,
    "cancel_shutdown": system.cancel_shutdown,
    "set_reminder":  reminders.set_reminder,
    "set_timer":     reminders.set_timer,
    "list_reminders": reminders.list_reminders,
    "remember":      memory.remember,
    "recall":        memory.recall,
    "forget":        memory.forget,
}

# Actions that are destructive and need a spoken "yes" first
NEEDS_CONFIRMATION = {"delete_file", "shutdown_pc", "restart_pc"}


def run(action: str, args: dict) -> str:
    fn = REGISTRY.get(action)
    if fn is None:
        return f"I don't know how to do '{action}' yet."
    try:
        return fn(**args)
    except TypeError as e:
        return f"I couldn't run that — missing details. ({e})"
    except Exception as e:
        return f"Something went wrong: {e}"
