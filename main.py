"""Nova — main loop.

Run:  python main.py           (voice mode — wake word "Nova")
      python main.py --text    (text mode — type instead of speak, for testing)
"""
import datetime
import difflib
import socket
import sys

import config
import intents
import tools
from brain import Brain
from tts import Speaker

# ── single-instance lock ────────────────────────────────────
# Two Novas answering at once = overlapping mixed voices. The port bind
# acts as a system-wide lock: a second copy exits immediately.
_instance_lock = socket.socket()
try:
    _instance_lock.bind(("127.0.0.1", 52789))
except OSError:
    print("Nova is already running — this duplicate will exit.")
    sys.exit(0)


def time_greeting() -> str:
    h = datetime.datetime.now().hour
    if h < 12:
        part = "Good morning"
    elif h < 17:
        part = "Good afternoon"
    else:
        part = "Good evening"
    return f"{part} {config.USER_NAME}! I'm {config.ASSISTANT_NAME}. How are you feeling today?"


def handle(decision: dict, brain: Brain, speaker: Speaker, get_input,
           speak_fn=None) -> None:
    """Speak the reply and run the tool (with confirmation for deletes).
    speak_fn lets voice mode pass an interruptible speaker."""
    say = speak_fn or speaker.say
    action, args = decision["action"], decision["args"]

    if action in tools.NEEDS_CONFIRMATION:
        say(decision["speak"] or f"Should I {action.replace('_', ' ')} {args.get('name', '')}? Say yes to confirm.")
        answer = get_input().lower()
        if not any(w in answer for w in ("yes", "yeah", "sure", "go ahead", "confirm", "do it")):
            say("Okay, cancelled.")
            return
        result = tools.run(action, args)
        say(result)
        return

    if action != "none":
        # speak only the tool's REAL result — the model's own "speak" for
        # actions tends to hallucinate (wrong time, "already created", etc.)
        result = tools.run(action, args)
        say(result)
    elif decision["speak"]:
        say(decision["speak"])
    else:
        # never go silent — silence reads as 'Nova is broken'
        say("Sorry, I didn't catch that. Could you say it again?")


def main():
    text_mode = "--text" in sys.argv

    speaker = Speaker()
    brain = Brain()
    # pre-load the LLM while Nova greets — first answer comes fast
    import threading
    threading.Thread(target=brain.warm_up, daemon=True).start()

    if text_mode:
        get_input = lambda: input("  You: ").strip()
        speak_fn = speaker.say
    else:
        from stt import Listener, ensure_whisper_server  # mic-only imports
        if config.STT_ENGINE == "whisper" and config.WHISPER_AUTOSTART:
            ensure_whisper_server()
        listener = Listener()
        get_input = listener.listen_command

        def speak_fn(text):
            """Interruptible speech: saying 'stop'/'wait' alone cuts Nova off."""
            ev = listener.start_interrupt_watch()
            try:
                interrupted = speaker.say(text, stop_event=ev)
            finally:
                listener.stop_interrupt_watch()
            if interrupted:
                print("  [interrupted]")
            return interrupted

    # ── greeting + mood ─────────────────────────────────────
    speaker.say(time_greeting())
    mood = get_input()
    if mood:
        if not text_mode:
            print(f"  You: {mood}")
        # the user may answer the greeting with a COMMAND ("play some
        # music") — honour it instead of only chatting about it
        intent = intents.parse(mood)
        if intent:
            action, args = intent
            handle({"speak": "", "action": action, "args": args},
                   brain, speaker, get_input, speak_fn=speak_fn)
        else:
            decision = brain.think(f"(user's mood/answer to 'how are you feeling') {mood}")
            speaker.say(decision["speak"] or "Good to hear. I'm here whenever you need me.")
    else:
        speaker.say("No worries. I'm here whenever you need me.")

    # ── main loop ───────────────────────────────────────────
    # follow-up mode: right after Nova speaks, keep listening for a few
    # seconds so the user can continue WITHOUT saying the wake word again
    follow_up = True  # the greeting just happened, so listen directly
    while True:
        try:
            if text_mode:
                command = get_input()
            elif follow_up:
                command = listener.listen_command()
                if not command:
                    follow_up = False  # user went quiet → back to wake word
                    continue
            else:
                spoken_after_wake = listener.wait_for_wake_word()
                # same-breath text comes from Vosk and is often garbled —
                # trust it ONLY if it cleanly matches a known command;
                # otherwise re-listen with Whisper (accurate)
                if spoken_after_wake and intents.parse(spoken_after_wake):
                    command = spoken_after_wake
                else:
                    speaker.say("Yes?")
                    command = listener.listen_command()
            if not command:
                continue
            # echo guard: if the mic picked up Nova's OWN voice (speaker
            # echo), ignore it instead of replying to ourselves
            last = getattr(speaker, "last_text", "")
            if last and difflib.SequenceMatcher(
                    None, command.lower(), last.lower()).ratio() > 0.75:
                continue
            if not text_mode:
                print(f"  You: {command}")
            # NOTE: "shut down" is NOT an exit word — it belongs to the PC
            # shutdown intent. Exiting Nova is goodbye/exit/quit only.
            if command.lower().strip(" .!?,") in ("exit", "quit", "goodbye", "good bye"):
                speaker.say(f"Goodbye {config.USER_NAME}, see you soon!")
                break

            # 1) try fast deterministic rules (time, play, create, delete...)
            intent = intents.parse(command)
            if intent:
                action, args = intent
                decision = {"speak": "", "action": action, "args": args}
            else:
                # 2) anything else (chat, mood, questions) → the LLM
                t0 = datetime.datetime.now()
                decision = brain.think(command)
                took = (datetime.datetime.now() - t0).total_seconds()
                print(f"  [brain {took:.1f}s]")
            handle(decision, brain, speaker, get_input, speak_fn=speak_fn)
            # Nova just replied — listen directly for a follow-up (also
            # covers barge-in: the replacement command comes right away)
            follow_up = True

        except KeyboardInterrupt:
            speaker.say("Goodbye!")
            break
        except Exception as e:
            print(f"  [error] {e}")
            speaker.say("Sorry, something went wrong. Try again.")


if __name__ == "__main__":
    main()
