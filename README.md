# Nova — Offline Voice Assistant

A lightweight Jarvis-style voice assistant that runs fully on your PC
(under 2 GB RAM). Speech recognition and the AI brain are 100% offline;
internet is only used when you ask for web things (songs, maps, search).

## How it works
```
"Nova"      → Vosk wake word (offline, ~40MB)
Your command→ Whisper base (offline, local server, best accuracy)
            → fast intent rules, else Ollama gemma3:1b (the brain)
            → Tools (files, browser, apps, time)
            → Windows SAPI voice reply (offline)
```
The Whisper server runs under Python 3.12 (`py -3.12 whisper_server.py`)
and is auto-started by Nova. STT engine is switchable in `config.py`
(`whisper` / `google` / `vosk` — all fall back to offline vosk on failure).

## Setup
1. Install [Ollama](https://ollama.com) and pull the model:
   `ollama pull gemma3:1b`
2. Install Python packages:
   `pip install -r requirements.txt`
3. The Vosk speech model lives in `models/vosk-model-small-en-us-0.15`
   (downloaded during setup — see below if missing):
   https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip

## Run
```
python main.py          # voice mode — say "Nova" then your command
python main.py --text   # text mode — type commands (testing without mic)
```

## Things you can say
- "Nova, create a folder called projects"
- "Nova, delete old notes from my downloads"  (asks for confirmation, goes to Recycle Bin)
- "Nova, play lo-fi hip hop"
- "Nova, open maps to the nearest coffee shop"
- "Nova, search how to learn python"
- "Nova, open calculator"
- "Nova, what time is it"
- "goodbye" — exits

## Config
Edit `config.py` — assistant name, wake words, Ollama model, voice, speech rate.
