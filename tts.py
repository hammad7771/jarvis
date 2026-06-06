"""Nova — text-to-speech.

Two modes (config.TTS_MODE):
  "neural" — Microsoft Edge neural voices via edge-tts: sounds human,
             needs internet. Falls back to SAPI automatically when offline.
  "sapi"   — Windows built-in voice: fully offline, instant.

MP3 playback uses winmm (built into Windows) — no extra audio deps.
"""
import asyncio
import ctypes
import tempfile
import time
import uuid
from pathlib import Path

import win32com.client

import config

_SAPI_ASYNC, _SAPI_PURGE = 1, 2


def _mci(cmd: str):
    ctypes.windll.winmm.mciSendStringW(cmd, None, 0, None)


def _mci_mode(alias: str) -> str:
    buf = ctypes.create_unicode_buffer(32)
    ctypes.windll.winmm.mciSendStringW(f"status {alias} mode", buf, 32, None)
    return buf.value


def _play_mp3(path: str, stop_event=None) -> bool:
    """Play an mp3; abort early if stop_event fires. True = interrupted."""
    alias = f"nova_{uuid.uuid4().hex[:8]}"
    _mci(f'open "{path}" type mpegvideo alias {alias}')
    _mci(f"play {alias}")
    interrupted = False
    while _mci_mode(alias) == "playing":
        if stop_event is not None and stop_event.is_set():
            _mci(f"stop {alias}")
            interrupted = True
            break
        time.sleep(0.1)
    _mci(f"close {alias}")
    return interrupted


class Speaker:
    def __init__(self):
        self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
        self.sapi.Rate = 1
        voices = self.sapi.GetVoices()
        if config.TTS_VOICE_INDEX < voices.Count:
            self.sapi.Voice = voices.Item(config.TTS_VOICE_INDEX)
        self._tmpdir = Path(tempfile.gettempdir()) / "nova_tts"
        self._tmpdir.mkdir(exist_ok=True)
        for old in self._tmpdir.glob("*.mp3"):   # clear leftovers from crashes
            old.unlink(missing_ok=True)

    # ── engines ─────────────────────────────────────────────
    def _say_neural(self, text: str, stop_event=None) -> bool:
        import edge_tts

        async def synth(out: str):
            communicate = edge_tts.Communicate(text, config.NEURAL_VOICE)
            await communicate.save(out)

        out = str(self._tmpdir / f"{uuid.uuid4().hex[:12]}.mp3")
        # tight timeout: if the service is slow, fall back to the instant
        # offline voice rather than making the user wait
        asyncio.run(asyncio.wait_for(synth(out), timeout=5))
        interrupted = _play_mp3(out, stop_event)
        Path(out).unlink(missing_ok=True)
        return interrupted

    def _say_sapi(self, text: str, stop_event=None) -> bool:
        if stop_event is None:
            self.sapi.Speak(text)
            return False
        self.sapi.Speak(text, _SAPI_ASYNC)
        while not self.sapi.WaitUntilDone(100):   # 100ms polls until done
            if stop_event.is_set():
                self.sapi.Speak("", _SAPI_ASYNC | _SAPI_PURGE)  # cut off
                return True
        return False

    # ── public API ──────────────────────────────────────────
    def say(self, text: str, stop_event=None) -> bool:
        """Speak text out loud (blocks until done). If stop_event is given
        and fires mid-speech, playback is cut off and True is returned."""
        if not text:
            return False
        # normalise curly quotes, then drop anything the Windows console /
        # SAPI can't handle (emojis etc. — small LLMs sneak them in)
        clean = text.replace("’", "'").replace("‘", "'") \
                    .replace("“", '"').replace("”", '"')
        clean = clean.encode("cp1252", errors="ignore").decode("cp1252").strip()
        if not clean:
            return False
        self.last_text = clean   # used by main's echo guard
        print(f"  {config.ASSISTANT_NAME}: {clean}")
        if config.TTS_MODE == "neural":
            try:
                return self._say_neural(clean, stop_event)
            except Exception:
                pass  # offline or service hiccup → fall back to SAPI
        return self._say_sapi(clean, stop_event)

    def list_voices(self):
        """Print available Windows SAPI voices (for TTS_VOICE_INDEX)."""
        voices = self.sapi.GetVoices()
        for i in range(voices.Count):
            print(f"  [{i}] {voices.Item(i).GetDescription()}")


if __name__ == "__main__":
    s = Speaker()
    s.say("Hi Hamza, this is my new neural voice. Do I sound more natural now?")
    s.say("And here is a second sentence, to prove repeated speech still works.")
