"""One-off: benchmark Ollama cloud models for Nova's brain (speed + JSON)."""
import json
import time

import requests

MODELS = [
    "gpt-oss:120b-cloud",
    "gpt-oss:120b-cloud",      # repeated = warm timing
    "qwen3-coder-next:cloud",
    "qwen3-coder-next:cloud",
]
MESSAGES = [
    {"role": "system",
     "content": 'Reply ONLY with JSON: {"speak": "...", "action": "none", "args": {}}'},
    {"role": "user", "content": "hello how are you"},
]

for m in MODELS:
    t0 = time.time()
    try:
        r = requests.post(
            "http://localhost:11434/api/chat",
            json={"model": m, "messages": MESSAGES,
                  "format": "json", "stream": False},
            timeout=30,
        )
        r.raise_for_status()
        json.loads(r.json()["message"]["content"])  # must be valid JSON
        print(f"{m:32} {time.time()-t0:5.1f}s  JSON-OK")
    except Exception as e:
        print(f"{m:32} {time.time()-t0:5.1f}s  FAILED: {type(e).__name__}")
