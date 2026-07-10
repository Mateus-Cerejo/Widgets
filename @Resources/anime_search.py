"""
Searches the Jikan API (MyAnimeList) for an anime by name, downloads its
cover art, and writes anime_info.json / anime_cover.jpg for the Watching
skin to show. Run with the search terms as arguments, or --clear to
deselect the current anime.
"""

import json
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

RESOURCES_DIR = Path(__file__).parent
INFO_FILE = RESOURCES_DIR / "anime_info.json"
COVER_FILE = RESOURCES_DIR / "anime_cover.jpg"
SEARCH_URL = "https://api.jikan.moe/v4/anime?limit=1&order_by=popularity&q="
USER_AGENT = "Rainmeter Watching widget"


def write_info(selected, title):
    with open(INFO_FILE, "w", encoding="utf-8") as f:
        json.dump({"AnimeSelected": selected, "AnimeTitle": title}, f, indent=2)


def fetch(url, attempts=4):
    # Jikan is a free API and intermittently returns 429/504 when it
    # can't reach MyAnimeList; retrying usually gets through
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(attempts):
        try:
            return urllib.request.urlopen(request, timeout=10)
        except Exception:
            if attempt == attempts - 1:
                raise
            time.sleep(3)


def crop_cover_to_square():
    """Center-crops anime_cover.jpg to a square with System.Drawing
    (same dependency-free approach as set_game.py's icon extraction)."""
    script = (
        "Add-Type -AssemblyName System.Drawing; "
        f"$bytes = [System.IO.File]::ReadAllBytes('{COVER_FILE}'); "
        "$ms = New-Object System.IO.MemoryStream(,$bytes); "
        "$img = [System.Drawing.Image]::FromStream($ms); "
        "$side = [Math]::Min($img.Width, $img.Height); "
        "$side = [int]($side / 2); "
        "$x = [int](($img.Width - $side) / 2); "
        "$y = [int](($img.Height - $side) / 4); "
        "$bmp = New-Object System.Drawing.Bitmap($side, $side); "
        "$g = [System.Drawing.Graphics]::FromImage($bmp); "
        "$src = New-Object System.Drawing.Rectangle($x, $y, $side, $side); "
        "$dst = New-Object System.Drawing.Rectangle(0, 0, $side, $side); "
        "$g.DrawImage($img, $dst, $src, [System.Drawing.GraphicsUnit]::Pixel); "
        "$g.Dispose(); $img.Dispose(); $ms.Dispose(); "
        f"$bmp.Save('{COVER_FILE}', [System.Drawing.Imaging.ImageFormat]::Jpeg); "
        "$bmp.Dispose()"
    )
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command", script],
        capture_output=True,
        timeout=15,
        check=True,
    )


def search_anime(query):
    with fetch(SEARCH_URL + urllib.parse.quote(query)) as response:
        results = json.load(response)["data"]
    if not results:
        return None
    anime = results[0]
    # Quotes would break the RegExp in Watching.ini
    title = anime["title"].replace('"', "'")
    image_url = anime["images"]["jpg"]["large_image_url"]
    return title, image_url


def main():
    args = [arg for arg in sys.argv[1:] if arg.strip()]
    if not args:
        print("No search terms given")
        return

    if args[0] == "--clear":
        write_info(0, "")
        print("Cleared selection")
        return

    query = " ".join(args)
    try:
        result = search_anime(query)
    except Exception as e:
        print(f"Jikan search failed: {e}")
        return

    if result is None:
        print(f"No results for '{query}'")
        return

    title, image_url = result
    try:
        with fetch(image_url) as response:
            COVER_FILE.write_bytes(response.read())
    except Exception as e:
        print(f"Could not download cover art: {e}")
        return

    try:
        crop_cover_to_square()
    except Exception as e:
        # A full-height cover still displays fine, just smaller
        print(f"Could not crop cover art: {e}")

    write_info(1, f" - {title}")
    print(f"Set anime to '{title}'")


if __name__ == "__main__":
    main()
