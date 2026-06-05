"""Nova — STT engine shoot-out.

Run:  python stt_benchmark.py
Speak the test sentence ONCE after the beep. The SAME recording is sent
to all three engines so the comparison is fair: accuracy + speed.
"""
import time

from stt import Listener, beep_listen  # noqa: F401  (Listener handles beeps)
import config

TEST_SENTENCE = "create a folder called my projects on the desktop and play some music"


def main():
    listener = Listener()
    print(f'\n=== After the beep, say:\n    "{TEST_SENTENCE}"\n')
    raw = listener.record_until_silence(max_seconds=15)
    if not raw:
        print("Heard nothing — check mic and try again (speak right after the beep).")
        return
    print(f"\nRecorded {len(raw) / 2 / config.SAMPLE_RATE:.1f}s of audio. Transcribing...\n")

    engines = [
        ("vosk (offline)", listener.transcribe_vosk),
        ("google (online)", listener.transcribe_google),
        ("whisper (local server)", listener.transcribe_whisper),
    ]
    print(f"{'ENGINE':<24} {'TIME':>7}  TEXT")
    print("-" * 80)
    for name, fn in engines:
        t0 = time.time()
        try:
            text = fn(raw)
            took = f"{time.time() - t0:.2f}s"
        except Exception as e:
            text = f"FAILED — {type(e).__name__}: {e}"
            took = "-"
        print(f"{name:<24} {took:>7}  {text}")

    print(f"\nTarget was: {TEST_SENTENCE}")
    print("Pick the winner and set STT_ENGINE in config.py accordingly.")


if __name__ == "__main__":
    main()
