"""Nova — persistent memory across sessions.

Facts live in nova_memory.json next to the code. They're injected into
the brain's system prompt, so Nova can use them in any conversation.
"""
import datetime
import json
from pathlib import Path

FILE = Path(__file__).parent.parent / "nova_memory.json"
MAX_FACTS = 50


def _load() -> list[dict]:
    if FILE.exists():
        try:
            return json.loads(FILE.read_text(encoding="utf-8"))
        except ValueError:
            return []
    return []


def _save(facts: list[dict]):
    FILE.write_text(json.dumps(facts, indent=2, ensure_ascii=False),
                    encoding="utf-8")


def all_facts() -> list[str]:
    """Plain fact strings — used by the brain's system prompt."""
    return [f["fact"] for f in _load()]


def remember(fact: str) -> str:
    fact = fact.strip().rstrip(".")
    if not fact:
        return "What should I remember?"
    facts = _load()
    if any(f["fact"].lower() == fact.lower() for f in facts):
        return "I already remember that."
    facts.append({"fact": fact,
                  "date": datetime.date.today().isoformat()})
    _save(facts[-MAX_FACTS:])   # keep the most recent N
    return f"Okay, I'll remember that {fact}."


def recall() -> str:
    facts = all_facts()
    if not facts:
        return "I don't have anything remembered yet. Say 'remember that' and a fact."
    listed = "; ".join(facts[-10:])
    more = f" — and {len(facts) - 10} older things" if len(facts) > 10 else ""
    return f"Here's what I remember: {listed}{more}."


def forget(keyword: str) -> str:
    keyword = keyword.strip().lower()
    facts = _load()
    kept = [f for f in facts if keyword not in f["fact"].lower()]
    removed = len(facts) - len(kept)
    if not removed:
        return f"I don't have anything about {keyword}."
    _save(kept)
    return f"Forgotten — removed {removed} thing{'s' if removed > 1 else ''} about {keyword}."
