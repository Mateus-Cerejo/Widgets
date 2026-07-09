"""
Fetches live stats from AnkiConnect (http://localhost:8765) for a single
deck and writes them to anki_stats.json for Rainmeter to read.

Requires Anki to be running with the AnkiConnect add-on installed.
"""

import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

OUTPUT_FILE = Path(__file__).parent / "anki_stats.json"
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "AJT JP1K"
ROLLOVER_HOUR = 4  # must match Anki's "Next day starts at" preference

CARD_QUERIES = {
    "AnkiDue": f'deck:"{DECK_NAME}" is:due -is:suspended',
    "AnkiNew": f'deck:"{DECK_NAME}" is:new -is:suspended',
    "AnkiLearning": f'deck:"{DECK_NAME}" is:learn -is:suspended',
    "AnkiLearnedToday": f'deck:"{DECK_NAME}" introduced:1',
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


def day_start_ms():
    """Epoch milliseconds of when the current Anki day started."""
    now = datetime.now()
    start = now.replace(hour=ROLLOVER_HOUR, minute=0, second=0, microsecond=0)
    if now < start:
        start -= timedelta(days=1)
    return int(start.timestamp() * 1000)


def count_reviews_today():
    """Reviews done today, matching Anki's own "Studied N cards today".

    Counts review-log entries (a card answered 3 times counts 3) and skips
    manual scheduling entries (type 4 = manual, 5 = rescheduled), which
    Anki's counter also excludes.
    """
    reviews = invoke("cardReviews", deck=DECK_NAME, startID=day_start_ms())
    return sum(1 for review in reviews if review[8] < 4)


def fetch_stats():
    counts = {name: len(invoke("findCards", query=query)) for name, query in CARD_QUERIES.items()}
    # Key order must match the RegExp in Anki.ini
    return {
        "AnkiDue": counts["AnkiDue"],
        "AnkiNew": counts["AnkiNew"],
        "AnkiLearning": counts["AnkiLearning"],
        "AnkiReviewedToday": count_reviews_today(),
        "AnkiLearnedToday": counts["AnkiLearnedToday"],
        "AnkiLastSync": datetime.now().strftime("%Y-%m-%d %H:%M"),
    }


def main():
    try:
        stats = fetch_stats()
    except Exception as e:
        # Leave the previous stats (and last sync time) on disk untouched
        print(f"Could not reach AnkiConnect at {ANKI_CONNECT_URL}: {e}")
        return

    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2)
    print(f"Wrote {stats} to {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
