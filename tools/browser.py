"""Nova — web actions: music, maps, search. Opens the default browser."""
import re
import webbrowser
from urllib.parse import quote_plus

import requests


def _first_youtube_id(query: str) -> str | None:
    """Scrape the first video id from YouTube search results (no API key)."""
    try:
        html = requests.get(
            f"https://www.youtube.com/results?search_query={quote_plus(query)}",
            headers={"User-Agent": "Mozilla/5.0"},
            timeout=8,
        ).text
        m = re.search(r'"videoId":"([\w-]{11})"', html)
        return m.group(1) if m else None
    except requests.RequestException:
        return None


def play_song(query: str) -> str:
    video_id = _first_youtube_id(query)
    if video_id:
        webbrowser.open(f"https://www.youtube.com/watch?v={video_id}")
        return f"Playing {query} on YouTube."
    # fallback: at least show the search results
    webbrowser.open(f"https://www.youtube.com/results?search_query={quote_plus(query)}")
    return f"Searching YouTube for {query}."


def open_maps(query: str) -> str:
    webbrowser.open(f"https://www.google.com/maps/search/{quote_plus(query)}")
    return f"Opening maps for {query}."


def search_web(query: str) -> str:
    webbrowser.open(f"https://www.google.com/search?q={quote_plus(query)}")
    return f"Here's what I found for {query}."


def open_website(url: str) -> str:
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    webbrowser.open(url)
    return f"Opening {url}."
