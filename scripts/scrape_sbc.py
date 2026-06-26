"""
Scrape Southern Baptist Convention annual resolutions from sbc.net.
Resolutions are passed at annual meetings (typically June).
The Conservative Resurgence (1979–1990) serves as SBC's internal rupture candidate.
Covers 1845–present.
"""

import re
import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

BASE = "https://www.sbc.net"
OUT = Path(__file__).parent.parent / "data" / "raw" / "sbc"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Academic research corpus (contact: benedict.r.leonardi@gmail.com)"}

RESOLUTIONS_INDEX = "https://www.sbc.net/resource-library/resolutions/"


def fetch(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            return None
        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    return None


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    text = soup.get_text(separator=" ")
    return re.sub(r"\s+", " ", text).strip()


def scrape_resolution(url: str) -> str | None:
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    # SBC resolution content is in .entry-content or article tags
    content = soup.find("div", class_="entry-content") or soup.find("article")
    if content:
        return re.sub(r"\s+", " ", content.get_text(separator=" ")).strip()
    return clean_text(soup)


def get_all_resolution_links() -> list[dict]:
    """
    SBC indexes resolutions by year at:
      https://www.sbc.net/{YEAR}/?post_type=mere_resource
    Covers 1845–present.
    """
    links = []
    current_year = 2026
    for year in range(1845, current_year + 1):
        url = f"{BASE}/{year}/?post_type=mere_resource"
        html = fetch(url)
        if not html:
            continue
        soup = BeautifulSoup(html, "html.parser")

        found = 0
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if "/resource-library/resolutions/" in href and title and len(title) > 5:
                full = href if href.startswith("http") else BASE + href
                links.append({"url": full, "title": title, "year": year})
                found += 1

        if found:
            print(f"  {year}: {found} resolutions")
        time.sleep(0.5)

    return links


def scrape_all():
    print("Fetching SBC resolution index...")
    links = get_all_resolution_links()
    # Deduplicate
    seen = set()
    unique = []
    for l in links:
        if l["url"] not in seen:
            seen.add(l["url"])
            unique.append(l)
    print(f"Found {len(unique)} resolutions")

    manifest = []
    for item in unique:
        slug = re.sub(r"[^a-z0-9]+", "_", item["title"].lower())[:60].strip("_")
        fname = f"{item['year']}_{slug}.txt"
        fpath = OUT / fname

        if fpath.exists():
            print(f"  Exists: {fname}")
        else:
            print(f"Fetching: {item['title']} ({item['year']})...")
            text = scrape_resolution(item["url"])
            if text:
                fpath.write_text(text, encoding="utf-8")
                print(f"  Saved: {fname} ({len(text.split()):,} words)")
            else:
                print(f"  FAILED: {item['url']}")
            time.sleep(1.0)

        manifest.append({
            "tradition": "sbc",
            "year": item["year"],
            "title": item["title"],
            "url": item["url"],
            "file": fname,
            "conservative_resurgence": 1979 <= item["year"] <= 1990,
        })

    manifest_path = OUT.parent.parent / "corpus" / "sbc_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest written: {manifest_path}")


if __name__ == "__main__":
    scrape_all()
