"""Nova — the brain. Sends user speech to Ollama and gets back a JSON
decision: what to say + which tool to run (if any).

If config.BIG_MODEL is installed and the PC has free RAM, it's used for
smarter replies; otherwise the small model runs. Checked per request, so
Nova adapts as you open/close other programs."""
import ctypes
import json
import time

import requests

import config


class _MEMORYSTATUSEX(ctypes.Structure):
    _fields_ = [("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)]


def free_ram_gb() -> float:
    stat = _MEMORYSTATUSEX()
    stat.dwLength = ctypes.sizeof(stat)
    ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
    return stat.ullAvailPhys / 1e9

SYSTEM_PROMPT = f"""You are {config.ASSISTANT_NAME}, a friendly voice assistant on {config.USER_NAME}'s Windows PC.
You hear the user through a microphone and your replies are spoken out loud,
so keep "speak" SHORT (one or two sentences), natural and warm. No emojis, no markdown.

You MUST reply with ONLY a JSON object in exactly this shape:
{{"speak": "<what to say out loud>", "action": "<action name or none>", "args": {{}}}}

Available actions and their args:
- create_folder  {{"name": "...", "folder": "desktop|downloads|documents|pictures|music|videos"}}
- create_file    {{"name": "notes.txt", "folder": "...", "content": "optional text"}}
- delete_file    {{"name": "...", "folder": "..."}}
- list_files     {{"folder": "..."}}
- play_song      {{"query": "song name"}}
- open_maps      {{"query": "place name"}}
- search_web     {{"query": "..."}}
- open_website   {{"url": "..."}}
- open_app       {{"name": "notepad|calculator|paint|explorer|task manager|settings"}}
- get_time       {{}}
- get_date       {{}}

Rules:
- If the user just wants to chat (mood, greetings, questions), use action "none" and only talk.
- "folder" defaults to desktop if the user doesn't say one.
- For music requests use play_song. For directions or places use open_maps.
- Never invent actions that are not in the list.
- ALWAYS include every required arg — especially "name" and "query".
- When the result of an action is given to you, summarise it naturally in "speak" with action "none".

Examples:
User: create a folder called school work
You: {{"speak": "Creating a folder called school work on your desktop.", "action": "create_folder", "args": {{"name": "school work", "folder": "desktop"}}}}
User: play shape of you
You: {{"speak": "Playing shape of you on YouTube.", "action": "play_song", "args": {{"query": "shape of you"}}}}
User: delete my old resume from downloads
You: {{"speak": "Should I delete old resume from your downloads? Say yes to confirm.", "action": "delete_file", "args": {{"name": "old resume", "folder": "downloads"}}}}
User: I'm feeling tired today
You: {{"speak": "Sorry to hear that. Maybe take a short break — I can put on some relaxing music if you like.", "action": "none", "args": {{}}}}
"""


class Brain:
    def __init__(self):
        self.history: list[dict] = []
        self._big_installed: bool | None = None  # checked lazily, once
        self._cloud_failed_at: float = 0.0       # last cloud failure time

    def _cloud_available(self) -> bool:
        return bool(config.CLOUD_MODEL) and \
            (time.time() - self._cloud_failed_at) > config.CLOUD_COOLDOWN

    def _pick_model(self) -> str:
        if not config.BIG_MODEL:
            return config.OLLAMA_MODEL
        if self._big_installed is None:
            try:
                tags = requests.get(config.OLLAMA_URL.replace("/api/chat", "/api/tags"),
                                    timeout=5).json()
                names = [m["name"] for m in tags.get("models", [])]
                self._big_installed = any(
                    n == config.BIG_MODEL or n.startswith(config.BIG_MODEL + ":")
                    for n in names)
            except Exception:
                self._big_installed = False
        if self._big_installed and free_ram_gb() >= config.BIG_MODEL_MIN_FREE_GB:
            return config.BIG_MODEL
        return config.OLLAMA_MODEL

    def _chat(self, messages: list[dict]) -> dict:
        # inject persistent memory so Nova actually uses what it remembers
        from tools.memory import all_facts
        facts = all_facts()
        system = SYSTEM_PROMPT
        if facts:
            system += "\nThings you remember about the user:\n" + \
                      "\n".join(f"- {f}" for f in facts[-10:])
        full_messages = [{"role": "system", "content": system}] + messages

        def post(model: str, timeout: float):
            resp = requests.post(
                config.OLLAMA_URL,
                json={
                    "model": model,
                    "messages": full_messages,
                    "format": "json",
                    "stream": False,
                    "keep_alive": "60m",   # keep model in RAM — no reload lag
                    # cap reply length (spoken replies are short) but leave
                    # headroom: too tight truncates the JSON mid-stream
                    "options": {"temperature": 0.4, "num_predict": 250},
                },
                timeout=timeout,
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

        # cloud first (smart + zero RAM); ANY failure → local for a while
        content = None
        if self._cloud_available():
            try:
                content = post(config.CLOUD_MODEL, config.CLOUD_TIMEOUT)
            except Exception:
                self._cloud_failed_at = time.time()
                print("  [cloud unavailable — using local model]")
        if content is None:
            content = post(self._pick_model(), 60)
        try:
            data = json.loads(content)
            if not isinstance(data, dict):
                raise json.JSONDecodeError("not an object", content, 0)
        except json.JSONDecodeError:
            # broken/truncated JSON: salvage the "speak" text instead of
            # reading raw JSON out loud
            import re
            m = re.search(r'"speak"\s*:\s*"((?:[^"\\]|\\.)*)', content)
            speak = (m.group(1).replace('\\"', '"').strip()
                     if m else "Sorry, I lost my train of thought. Ask me again?")
            data = {"speak": speak, "action": "none", "args": {}}
        # normalise
        return {
            "speak": str(data.get("speak", "")).strip(),
            "action": str(data.get("action", "none")).strip().lower() or "none",
            "args": data.get("args") or {},
        }

    def warm_up(self):
        """Pre-load the model into RAM at startup so the first real
        question doesn't pay the loading cost."""
        try:
            requests.post(
                config.OLLAMA_URL,
                json={"model": self._pick_model(),
                      "messages": [{"role": "user", "content": "hi"}],
                      "stream": False, "keep_alive": "60m",
                      "options": {"num_predict": 1}},
                timeout=120,
            )
        except requests.RequestException:
            pass

    def _remember(self, role: str, content: str):
        self.history.append({"role": role, "content": content})
        # keep history bounded so RAM and prompt size stay small
        if len(self.history) > config.MAX_HISTORY * 2:
            self.history = self.history[-config.MAX_HISTORY * 2:]

    def think(self, user_text: str) -> dict:
        """Main entry: user said something → decide speak/action/args."""
        self._remember("user", user_text)
        decision = self._chat(self.history)
        self._remember("assistant", json.dumps(decision))
        return decision

if __name__ == "__main__":
    b = Brain()
    print(b.think("hello nova how are you"))
    print(b.think("create a folder called test stuff on my desktop"))
