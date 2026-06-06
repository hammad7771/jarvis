"""Nova — speech-to-text with pluggable engines.

Wake word detection is ALWAYS offline Vosk (cheap, single word).
Command transcription uses config.STT_ENGINE:
    "google"  — free Google web speech API (best accuracy, needs internet)
    "whisper" — local whisper_server.py running under Python 3.12
    "vosk"    — fully offline (fallback for the other two on any error)
"""
import difflib
import json
import math
import queue
import struct
import subprocess
import sys
import threading
import time
import winsound
from pathlib import Path

import requests
import sounddevice as sd
from vosk import Model, KaldiRecognizer, SetLogLevel

import config

SetLogLevel(-1)  # hide Vosk's noisy internal loading logs


def beep_listen():
    """Short rising beep = 'Nova is listening, speak now'."""
    winsound.Beep(880, 120)


def beep_done():
    """Short falling beep = 'Nova stopped listening'."""
    winsound.Beep(440, 100)


def ensure_whisper_server(max_wait: float = 120.0) -> bool:
    """Start whisper_server.py (under Python 3.12) if it isn't running.
    Returns True when the server is healthy."""
    def healthy() -> bool:
        try:
            return requests.get(f"{config.WHISPER_URL}/health", timeout=2).ok
        except requests.RequestException:
            return False

    if healthy():
        return True
    server = Path(__file__).parent / "whisper_server.py"
    print("Starting Whisper server in the background (takes a few seconds)...")
    subprocess.Popen(
        ["py", "-3.12", str(server)],
        creationflags=subprocess.CREATE_NO_WINDOW,
        cwd=str(server.parent),
    )
    waited = 0.0
    while waited < max_wait:
        time.sleep(2)
        waited += 2
        if healthy():
            print("Whisper server ready.")
            return True
    print("Whisper server didn't come up — falling back to offline Vosk.")
    return False


def _rms(chunk: bytes) -> float:
    n = len(chunk) // 2
    if n == 0:
        return 0.0
    samples = struct.unpack(f"<{n}h", chunk)
    return math.sqrt(sum(s * s for s in samples) / n)


class Listener:
    def __init__(self):
        print("Loading speech model...")
        self.model = Model(config.VOSK_MODEL_DIR)
        self.q: queue.Queue = queue.Queue()

    # ── audio plumbing ──────────────────────────────────────
    def _callback(self, indata, frames, time_, status):
        if status:
            print(status, file=sys.stderr)
        self.q.put(bytes(indata))

    def _stream(self, blocksize: int = 8000):
        return sd.RawInputStream(
            samplerate=config.SAMPLE_RATE,
            blocksize=blocksize,
            dtype="int16",
            channels=1,
            callback=self._callback,
        )

    def _drain(self):
        """Throw away any buffered audio (e.g. captured while Nova spoke)."""
        while not self.q.empty():
            try:
                self.q.get_nowait()
            except queue.Empty:
                break

    # ── wake word (always offline Vosk) ─────────────────────
    @staticmethod
    def _find_wake(text: str) -> int:
        """Fuzzy wake-word search. Vosk garbles 'nova' into 'no i', 'now a',
        'no one', 'nover'... so we match single words AND adjacent word
        pairs against the name. Returns char index just AFTER the wake
        word, or -1 if not found."""
        name = config.ASSISTANT_NAME.lower()
        for w in config.WAKE_WORDS:           # literal variants first
            i = text.find(w)
            if i != -1:
                return i + len(w)
        for p in config.WAKE_PREFIXES:        # common garbles, start-only
            if text.startswith(p + " ") or text == p:
                return len(p)
        words = text.split()
        pos = 0
        for i, w in enumerate(words):
            start = text.index(w, pos)
            pos = start + len(w)
            if difflib.SequenceMatcher(None, w, name).ratio() >= 0.78:
                return pos
            if i + 1 < len(words):            # e.g. 'no' + 'va', 'no' + 'one'
                pair = w + words[i + 1]
                if difflib.SequenceMatcher(None, pair, name).ratio() >= 0.8:
                    return text.index(words[i + 1], pos) + len(words[i + 1])
        return -1

    def wait_for_wake_word(self) -> str:
        """Block until a wake word is heard. Returns any extra words
        spoken after the wake word in the same breath (may be '').
        Self-healing: if the mic stream dies (no audio for ~6s), it is
        reopened instead of waiting forever."""
        while True:
            result = self._wake_session()
            if result is not None:
                return result
            print("  [mic went quiet — restarting audio stream]")

    def _wake_session(self) -> str | None:
        """One wake-word listening session. None = stream died, reopen."""
        rec = KaldiRecognizer(self.model, config.SAMPLE_RATE)
        self._drain()
        last_partial = ""
        dead_polls = 0
        with self._stream():
            print(f"\n[listening for wake word — say '{config.ASSISTANT_NAME}']")
            while True:
                try:
                    data = self.q.get(timeout=3)
                    dead_polls = 0
                except queue.Empty:
                    dead_polls += 1
                    if dead_polls >= 2:   # ~6s with zero audio = dead stream
                        return None
                    continue
                if rec.AcceptWaveform(data):
                    text = json.loads(rec.Result()).get("text", "").lower()
                    end = self._find_wake(text)
                    if end != -1:
                        print()
                        return text[end:].strip()
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "").lower()
                    if partial and partial != last_partial:
                        last_partial = partial
                        print(f"\r  [hearing] {partial[-70:]:<70}", end="", flush=True)
                    # fire early only when the partial ENDS at the wake word,
                    # so a command in the same breath is still captured by
                    # the full-result branch above
                    end = self._find_wake(partial)
                    if end != -1 and not partial[end:].strip():
                        print()
                        return ""

    # ── interrupt watch (barge-in while Nova speaks) ────────
    def start_interrupt_watch(self) -> threading.Event:
        """Listen in the background for a lone interrupt word ('stop',
        'wait'...). Returns an Event that gets set when one is heard.
        The exact-match rule stops Nova's own speech (echoed into the
        mic as longer phrases) from triggering it."""
        self._int_fired = threading.Event()
        self._int_quit = threading.Event()

        def watch():
            rec = KaldiRecognizer(self.model, config.SAMPLE_RATE)
            self._drain()
            with self._stream(4000):
                while not self._int_quit.is_set():
                    try:
                        data = self.q.get(timeout=0.3)
                    except queue.Empty:
                        continue
                    if rec.AcceptWaveform(data):
                        heard = json.loads(rec.Result()).get("text", "").strip()
                    else:
                        heard = json.loads(rec.PartialResult()).get("partial", "").strip()
                    if heard in config.INTERRUPT_WORDS:
                        self._int_fired.set()
                        return

        self._int_thread = threading.Thread(target=watch, daemon=True)
        self._int_thread.start()
        return self._int_fired

    def stop_interrupt_watch(self):
        self._int_quit.set()
        self._int_thread.join(timeout=1.5)
        self._drain()

    # ── command capture ─────────────────────────────────────
    def record_until_silence(self, max_seconds: float = 12.0) -> bytes:
        """Record one utterance: waits for speech, stops after a pause.
        Returns raw 16kHz mono int16 PCM (b'' if nothing was said)."""
        self._drain()
        blocksize = 4000                       # 0.25s chunks → snappy VAD
        chunk_secs = blocksize / config.SAMPLE_RATE
        started = False
        silence = 0.0
        waited = 0.0
        elapsed = 0.0
        audio = bytearray()
        with self._stream(blocksize):
            beep_listen()
            print("[listening — speak after the beep]")
            while elapsed < max_seconds:
                try:
                    data = self.q.get(timeout=2)   # dead-stream protection
                except queue.Empty:
                    break
                elapsed += chunk_secs
                level = _rms(data)
                if not started:
                    waited += chunk_secs
                    if level >= config.VAD_THRESHOLD:
                        started = True
                        audio.extend(data)
                    elif waited >= config.VAD_START_TIMEOUT:
                        break                  # user never spoke
                else:
                    audio.extend(data)
                    if level < config.VAD_THRESHOLD:
                        silence += chunk_secs
                        if silence >= config.VAD_END_SILENCE:
                            break              # done talking
                    else:
                        silence = 0.0
        beep_done()
        return bytes(audio) if started else b""

    # ── transcription engines ───────────────────────────────
    def transcribe_vosk(self, raw: bytes) -> str:
        rec = KaldiRecognizer(self.model, config.SAMPLE_RATE)
        rec.AcceptWaveform(raw)
        return json.loads(rec.FinalResult()).get("text", "").strip()

    def transcribe_google(self, raw: bytes) -> str:
        import speech_recognition as sr
        r = sr.Recognizer()
        audio = sr.AudioData(raw, config.SAMPLE_RATE, 2)
        return r.recognize_google(audio, language="en-PK").strip()

    def transcribe_whisper(self, raw: bytes) -> str:
        resp = requests.post(f"{config.WHISPER_URL}/transcribe",
                             data=raw, timeout=60)
        resp.raise_for_status()
        return resp.json()["text"].strip()

    def listen_command(self, max_seconds: float = 12.0) -> str:
        """Capture one spoken command using the configured engine.
        Falls back to offline Vosk if the engine fails (no internet etc.)."""
        raw = self.record_until_silence(max_seconds)
        if not raw:
            return ""
        engine = config.STT_ENGINE
        t0 = time.time()
        try:
            if engine == "google":
                text = self.transcribe_google(raw)
            elif engine == "whisper":
                text = self.transcribe_whisper(raw)
            else:
                text = self.transcribe_vosk(raw)
            print(f"  [stt {time.time() - t0:.1f}s]")
            return text
        except Exception as e:
            print(f"  [{engine} failed: {type(e).__name__} — using offline vosk]")
            return self.transcribe_vosk(raw)


if __name__ == "__main__":
    l = Listener()
    l.wait_for_wake_word()
    print("Wake word heard! Say a command:")
    print("You said:", l.listen_command())
