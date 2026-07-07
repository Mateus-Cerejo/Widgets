"""
Fetches live stats from AnkiConnect (http://localhost:8765) for a single
deck and writes them to anki_stats.json for Rainmeter to read.

Requires Anki to be running with the AnkiConnect add-on installed.
"""

import json
import urllib.request
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "anki_stats.json"
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "AJT JP1K"

CARD_QUERIES = {
    "AnkiDue": f'deck:"{DECK_NAME}" is:due -is:suspended',
    "AnkiNew": f'deck:"{DECK_NAME}" is:new -is:suspended',
    "AnkiLearning": f'deck:"{DECK_NAME}" is:learn -is:suspended',
    "AnkiReviewedToday": f'deck:"{DECK_NAME}" rated:1',
}


def invoke(action, **params):
    payload = json.dumps({"action": action, "version": 6, "params": params}).encode("utf-8")
    request = urllib.request.Request(ANKI_CONNECT_URL, payload)
    with urllib.request.urlopen(request, timeout=5) as response:
        result = json.load(response)
    if len(result) != 2:
        raise Exception("AnkiConnect response has an unexpected number of fields")
    if result.get("error") is not None:
        raise Exception(result["error"])
    return result["result"]


def fetch_stats():
    return {name: len(invoke("findCards", query=query)) for name, query in CARD_QUERIES.items()}


def main():
    try:
        stats = fetch_stats()
    except Exception as e:
        print(f"Could not reach AnkiConnect at {ANKI_CONNECT_URL}: {e}")
        return;
        #stats = {name: "N/A" for name in CARD_QUERIES}

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {stats} to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
