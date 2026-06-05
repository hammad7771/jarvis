"""Nova — local Whisper transcription server.

MUST run under Python 3.12 (faster-whisper doesn't support 3.14 yet):
    py -3.12 whisper_server.py

Stdlib-only HTTP server: POST raw 16kHz mono int16 PCM to /transcribe,
get back JSON {"text": "..."}.  GET /health for a readiness check.
"""
import json
import time
from http.server import BaseHTTPRequestHandler, HTTPServer

import numpy as np
from faster_whisper import WhisperModel

HOST, PORT = "127.0.0.1", 8765
MODEL_SIZE = "base"  # ~74M params, int8 → ~200MB RAM. "tiny" = faster, "small" = better.

print(f"Loading Whisper '{MODEL_SIZE}' (first run downloads the model)...")
model = WhisperModel(MODEL_SIZE, device="cpu", compute_type="int8")
print("Whisper ready.")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):  # silence per-request logs
        pass

    def _json(self, code: int, payload: dict):
        body = json.dumps(payload).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._json(200, {"status": "ok", "model": MODEL_SIZE})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self):
        if self.path != "/transcribe":
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        raw = self.rfile.read(length)
        t0 = time.time()
        audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
        segments, _ = model.transcribe(audio, language="en", beam_size=1,
                                       vad_filter=True)
        text = " ".join(s.text.strip() for s in segments).strip()
        self._json(200, {"text": text, "seconds": round(time.time() - t0, 2)})


if __name__ == "__main__":
    print(f"Whisper server listening on http://{HOST}:{PORT}")
    HTTPServer((HOST, PORT), Handler).serve_forever()
