"""Nova — intent regression suite. Run: python test_intents.py"""
import intents

# (spoken text, expected action or None)
CASES = [
    # reminder/memory must beat play/delete (the hijack bugs)
    ("remind me in 10 minutes to play cricket", "set_reminder"),
    ("remind me to delete the old file in 2 hours", "set_reminder"),
    ("remember that i play football on sundays", "remember"),
    ("set a timer for 5 minutes", "set_timer"),
    ("what do you remember about me", "recall"),
    ("forget about my exam", "forget"),
    # core commands
    ("what time is it", "get_time"),
    ("what is the date today", "get_date"),
    ("play shape of you", "play_song"),
    ("navigate to the nearest hospital", "open_maps"),
    ("create a folder called uni work on my desktop", "create_folder"),
    ("create a file called notes.txt", "create_file"),
    ("delete old resume from downloads", "delete_file"),
    ("how many items are on my desktop", "list_files"),
    # window / settings / volume
    ("minimize this window", "minimize_window"),
    ("minimum screen", "minimize_window"),
    ("short desktop", "show_desktop"),
    ("show desktop", "show_desktop"),
    ("close this window", "close_window"),
    ("turn on dark mode", "set_dark_mode"),
    ("open wifi settings", "open_settings"),
    ("open settings", "open_settings"),
    ("set volume to 50 percent", "set_volume"),
    ("volume up", "volume_up"),
    ("make it louder", "volume_up"),
    ("mute", "mute"),
    ("set brightness to 70", "set_brightness"),
    ("lock my computer", "lock_pc"),
    ("take a screenshot", "take_screenshot"),
    ("shut down the pc in 10 minutes", "shutdown_pc"),
    ("restart my computer", "restart_pc"),
    ("cancel the shutdown", "cancel_shutdown"),
    # apps & web
    ("open chrome", "open_app"),
    ("open calculator", "open_app"),
    ("open youtube", "open_website"),
    ("search how to learn python", "search_web"),
    # chat → must fall through to the LLM
    ("i'm feeling tired today", None),
    ("tell me a joke", None),
    ("what's the capital of france", None),
]


def main():
    failed = 0
    for text, expected in CASES:
        got = intents.parse(text)
        got_action = got[0] if got else None
        if got_action != expected:
            failed += 1
            print(f"  FAIL {text!r}: expected {expected}, got {got}")
    total = len(CASES)
    print(f"{total - failed}/{total} passed" + (" — ALL OK" if not failed else ""))
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
