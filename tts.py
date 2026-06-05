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
import uuid
from pathlib import Path

import win32com.client

import config


def _play_mp3_blocking(path: str):
    mci = ctypes.windll.winmm.mciSendStringW
    alias = f"nova_{uuid.uuid4().hex[:8]}"
    mci(f'open "{path}" type mpegvideo alias {alias}', None, 0, None)
    mci(f"play {alias} wait", None, 0, None)
    mci(f"close {alias}", None, 0, None)


class Speaker:
    def __init__(self):
        self.sapi = win32com.client.Dispatch("SAPI.SpVoice")
        self.sapi.Rate = 1
        voices = self.sapi.GetVoices()
        if config.TTS_VOICE_INDEX < voices.Count:
            self.sapi.Voice = voices.Item(config.TTS_VOICE_INDEX)
        self._tmpdir = Path(tempfile.gettempdir()) / "nova_tts"
        self._tmpdir.mkdir(exist_ok=True)

    # ── engines ─────────────────────────────────────────────
    def _say_neural(self, text: str):
        import edge_tts

        async def synth(out: str):
            communicate = edge_tts.Communicate(text, config.NEURAL_VOICE)
            await communicate.save(out)

        out = str(self._tmpdir / f"{uuid.uuid4().hex[:12]}.mp3")
        # tight timeout: if the service is slow, fall back to the instant
        # offline voice rather than making the user wait
        asyncio.run(asyncio.wait_for(synth(out), timeout=5))
        _play_mp3_blocking(out)
        Path(out).unlink(missing_ok=True)

    def _say_sapi(self, text: str):
        self.sapi.Speak(text)

    # ── public API ──────────────────────────────────────────
    def say(self, text: str):
        """Speak text out loud (blocks until done)."""
        if not text:
            return
        # normalise curly quotes, then drop anything the Windows console /
        # SAPI can't handle (emojis etc. — small LLMs sneak them in)
        clean = text.replace("’", "'").replace("‘", "'") \
                    .replace("“", '"').replace("”", '"')
        clean = clean.encode("cp1252", errors="ignore").decode("cp1252").strip()
        if not clean:
            return
        self.last_text = clean   # used by main's echo guard
        print(f"  {config.ASSISTANT_NAME}: {clean}")
        if config.TTS_MODE == "neural":
            try:
                self._say_neural(clean)
                return
            except Exception:
                pass  # offline or service hiccup → fall back to SAPI
        self._say_sapi(clean)

    def list_voices(self):
        """Print available Windows SAPI voices (for TTS_VOICE_INDEX)."""
        voices = self.sapi.GetVoices()
        for i in range(voices.Count):
            print(f"  [{i}] {voices.Item(i).GetDescription()}")


if __name__ == "__main__":
    s = Speaker()
    s.say("Hi Hamza, this is my new neural voice. Do I sound more natural now?")
    s.say("And here is a second sentence, to prove repeated speech still works.")
