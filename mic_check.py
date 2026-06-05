"""Nova — microphone diagnostic.

Run:  python mic_check.py
Speak the test sentence when prompted. It reports:
  1. which microphone Windows is using
  2. how loud your voice arrives (level check)
  3. exactly what the speech model hears
"""
import json
import math
import struct
import winsound

import sounddevice as sd
from vosk import Model, KaldiRecognizer, SetLogLevel

import config

SetLogLevel(-1)  # hide Vosk's noisy internal loading logs

SECONDS = 6
TEST_SENTENCE = "hello nova what time is it"


def main():
    # 1 — devices
    print("=== Input devices ===")
    default_in = sd.default.device[0]
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            mark = "  <-- DEFAULT" if i == default_in else ""
            print(f"  [{i}] {d['name']}{mark}")

    # 2 — record
    print(f"\n=== After the beep, say clearly: \"{TEST_SENTENCE}\" ===")
    winsound.Beep(880, 200)
    rec_audio = sd.rec(int(SECONDS * config.SAMPLE_RATE),
                       samplerate=config.SAMPLE_RATE, channels=1, dtype="int16")
    sd.wait()
    winsound.Beep(440, 150)
    raw = rec_audio.tobytes()

    # 3 — level
    samples = struct.unpack(f"<{len(raw)//2}h", raw)
    rms = math.sqrt(sum(s * s for s in samples) / len(samples))
    peak = max(abs(s) for s in samples)
    print("\n=== Mic level ===")
    print(f"  RMS:  {rms:8.0f}   (good speech is roughly 500-5000)")
    print(f"  Peak: {peak:8d}   (out of 32767)")
    if peak < 500:
        print("  >>> VERY QUIET — wrong mic selected or mic volume near zero!")
    elif rms < 200:
        print("  >>> Quiet — raise mic volume in Windows Sound settings (boost to 100%).")
    else:
        print("  >>> Level looks OK.")

    # 4 — what the model hears
    print("\n=== What the speech model heard ===")
    model = Model(config.VOSK_MODEL_DIR)
    rec = KaldiRecognizer(model, config.SAMPLE_RATE)
    rec.AcceptWaveform(raw)
    heard = json.loads(rec.FinalResult()).get("text", "")
    print(f"  You said : {TEST_SENTENCE}")
    print(f"  It heard : {heard or '(nothing)'}")


if __name__ == "__main__":
    main()
