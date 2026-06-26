"""
Scrape ALL papal encyclicals from vatican.va by crawling each pope's index page.
Covers Leo XIII (1878) to present — the era of the modern encyclical form.
"""

import re
import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

BASE = "https://www.vatican.va"
OUT = Path(__file__).parent.parent / "data" / "raw" / "catholic"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Academic research corpus (contact: benedict.r.leonardi@gmail.com)"}

# Vatican per-pope encyclical index pages
# Pattern: /content/{pope-slug}/en/encyclicals.index.html
POPES = [
    ("leo_xiii",      1878, 1903, "leo-xiii"),
    ("pius_x",        1903, 1914, "pius-x"),
    ("benedict_xv",   1914, 1922, "benedict-xv"),
    ("pius_xi",       1922, 1939, "pius-xi"),
    ("pius_xii",      1939, 1958, "pius-xii"),
    ("john_xxiii",    1958, 1963, "john-xxiii"),
    ("paul_vi",       1963, 1978, "paul-vi"),
    ("john_paul_i",   1978, 1978, "john-paul-i"),
    ("john_paul_ii",  1978, 2005, "john-paul-ii"),
    ("benedict_xvi",  2005, 2013, "benedict-xvi"),
    ("francis",       2013, 2026, "francesco"),
]

# Known fallback index URLs for popes where the standard pattern fails
FALLBACK_INDEX = {
    "francesco": "https://www.vatican.va/content/francesco/en/encyclicals.index.html",
}


def fetch(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=30)
            if r.status_code == 200:
                return r.text
            print(f"  HTTP {r.status_code}: {url}")
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


def get_encyclical_links(pope_slug: str, vatican_slug: str) -> list[dict]:
    """
    Crawl the Vatican index page for a pope's encyclicals and return all doc links.
    Tries multiple URL patterns the Vatican uses.
    """
    index_urls = [
        f"{BASE}/content/{vatican_slug}/en/encyclicals.index.html",
        f"{BASE}/holy_father/{pope_slug}/encyclicals/index.htm",
        f"{BASE}/content/{vatican_slug}/en/encyclicals/index.html",
    ]
    if vatican_slug in FALLBACK_INDEX:
        index_urls.insert(0, FALLBACK_INDEX[vatican_slug])

    links = []
    for idx_url in index_urls:
        html = fetch(idx_url)
        if not html:
            continue

        soup = BeautifulSoup(html, "html.parser")
        for a in soup.find_all("a", href=True):
            href = a["href"]
            title = a.get_text(strip=True)
            if not title or len(title) < 4:
                continue
            # Skip non-English language links (zh, it, es, de, fr, pt, la, etc.)
            if re.search(r"/(zh|it|es|de|fr|pt|la|pl|ar|ru|ko|ja|vi)/", href):
                continue
            if re.search(r"enc_\d{8}|enc_\d{4}|_enc_", href, re.I):
                full = href if href.startswith("http") else BASE + href
                if "/en/" not in full and "/la/" in full:
                    full = full.replace("/la/", "/en/")
                links.append({"title": title, "url": full})

        if links:
            print(f"  Found {len(links)} links from {idx_url}")
            break

    # Deduplicate by URL
    seen, unique = set(), []
    for l in links:
        if l["url"] not in seen:
            seen.add(l["url"])
            unique.append(l)
    return unique


def infer_year(url: str, title: str, pope_start: int) -> int:
    """Extract year from URL date stamp (DDMMYYYY or YYYYMMDD patterns)."""
    # Vatican URLs often contain dates like _15051891_ or _19310515_
    m = re.search(r"_(\d{8})_", url)
    if m:
        digits = m.group(1)
        # Try DDMMYYYY first (most common Vatican pattern)
        try:
            year = int(digits[4:8])
            if pope_start - 2 <= year <= pope_start + 40:
                return year
        except Exception:
            pass
        # Try YYYYMMDD
        try:
            year = int(digits[0:4])
            if pope_start - 2 <= year <= pope_start + 40:
                return year
        except Exception:
            pass
    # Fall back to pope's start year
    return pope_start


def scrape_all():
    manifest = []
    for pope_slug, start_yr, end_yr, vatican_slug in POPES:
        print(f"\n=== {pope_slug.replace('_', ' ').title()} ({start_yr}–{end_yr}) ===")
        links = get_encyclical_links(pope_slug, vatican_slug)

        if not links:
            print(f"  No links found — check index URL for {vatican_slug}")
            continue

        for link in links:
            year = infer_year(link["url"], link["title"], start_yr)
            slug = re.sub(r"[^a-z0-9]+", "_", link["title"].lower())[:60].strip("_")
            fname = f"{year}_{pope_slug}_{slug}.txt"
            fpath = OUT / fname

            if fpath.exists():
                print(f"  Exists: {fname}")
            else:
                print(f"  Fetching: {link['title']} ({year})...")
                html = fetch(link["url"])
                if html:
                    soup = BeautifulSoup(html, "html.parser")
                    text = clean_text(soup)
                    if len(text.split()) < 50:
                        print(f"    Too short, skipping")
                        continue
                    fpath.write_text(text, encoding="utf-8")
                    print(f"    Saved: {fname} ({len(text.split()):,} words)")
                else:
                    print(f"    FAILED: {link['url']}")
                time.sleep(1.5)

            manifest.append({
                "tradition": "catholic",
                "pope": pope_slug,
                "title": link["title"],
                "year": year,
                "url": link["url"],
                "file": fname,
                "pre_vii": year < 1962,
                "council_period": 1962 <= year <= 1965,
                "post_vii": year > 1965,
            })

    manifest_path = OUT.parent.parent / "corpus" / "catholic_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {manifest_path} ({len(manifest)} encyclicals)")


if __name__ == "__main__":
    scrape_all()
