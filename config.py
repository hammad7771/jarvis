"""Nova — configuration"""
import os
from pathlib import Path

# ── Identity ────────────────────────────────────────────────
ASSISTANT_NAME = "Nova"
USER_NAME = "Hamza"

# ── Wake word ───────────────────────────────────────────────
# Words that trigger Nova (lowercase). Vosk sometimes hears
# "nova" as "over"/"nover", so we accept close variants.
WAKE_WORDS = ["nova", "hey nova", "nover", "novah", "noah", "over there nova",
              "no va", "nova's", "novel"]
# Vosk often garbles 'Nova' at the start of a sentence into these.
# They count as the wake word ONLY at the very beginning of speech.
WAKE_PREFIXES = ["no i", "no one", "now i", "no a", "now a", "know a",
                 "hey no", "and over", "nor a"]

# Saying any of these ALONE while Nova is talking cuts her off mid-speech.
INTERRUPT_WORDS = ["stop", "wait", "cancel", "quiet", "shut up",
                   "never mind", "nevermind", "okay stop", "nova stop"]

# ── LLM (Ollama) ────────────────────────────────────────────
OLLAMA_URL = "http://localhost:11434/api/chat"
OLLAMA_MODEL = "gemma3:1b"
MAX_HISTORY = 6           # conversation turns the brain remembers
                          # (smaller prompt = faster replies on CPU)

# Bigger brain auto-switch: when this model is installed AND your PC has
# enough free RAM, Nova uses it for smarter conversation; otherwise it
# silently sticks with OLLAMA_MODEL. (Install with: ollama pull gemma3:4b)
BIG_MODEL = "gemma3:4b"
BIG_MODEL_MIN_FREE_GB = 6.0

# Cloud brain (Ollama cloud, free account): much smarter, zero RAM,
# consistent ~3s. Needs internet + `ollama signin`. On ANY failure
# (offline, rate limit) Nova falls back to the local model for a while.
CLOUD_MODEL = "gpt-oss:120b-cloud"   # set to None to stay fully local
CLOUD_TIMEOUT = 12                   # seconds before giving up on cloud
CLOUD_COOLDOWN = 180                 # seconds to stay local after a failure

# ── Speech recognition engine ───────────────────────────────
# "google"  — free Google web API: best accuracy, needs internet
# "whisper" — local Whisper server (run: py -3.12 whisper_server.py)
# "vosk"    — fully offline; also the automatic fallback for the others
STT_ENGINE = "whisper"
WHISPER_URL = "http://127.0.0.1:8765"
WHISPER_AUTOSTART = True   # Nova starts whisper_server.py itself if not running

# Voice activity detection (when recording a command)
VAD_THRESHOLD = 300       # RMS above this = you are speaking (raise if noisy room)
VAD_START_TIMEOUT = 5.0   # seconds to wait for you to start talking
VAD_END_SILENCE = 0.8     # seconds of quiet that ends your command

# ── Voice output ────────────────────────────────────────────
# "neural" = human-sounding Microsoft voice (needs internet, auto-falls
#            back to offline SAPI). "sapi" = offline Windows voice only.
TTS_MODE = "neural"
NEURAL_VOICE = "en-US-AriaNeural"   # try: en-US-JennyNeural, en-GB-SoniaNeural,
                                    # en-IN-NeerjaNeural (South-Asian accent)

# ── Speech ──────────────────────────────────────────────────
# en-in = South-Asian English model (much better for Pakistani accent)
VOSK_MODEL_DIR = str(Path(__file__).parent / "models" / "vosk-model-small-en-in-0.4")
SAMPLE_RATE = 16000
TTS_VOICE_INDEX = 1       # offline fallback voice: 1 = Zira (female, matches
                          # the neural voice), 0 = David (male)

# ── Known user folders (used to resolve spoken file names) ──
HOME = Path.home()
KNOWN_FOLDERS = {
    "desktop": HOME / "Desktop",
    "downloads": HOME / "Downloads",
    "documents": HOME / "Documents",
    "pictures": HOME / "Pictures",
    "music": HOME / "Music",
    "videos": HOME / "Videos",
}
DEFAULT_FOLDER = KNOWN_FOLDERS["desktop"]
