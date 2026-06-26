"""
Scrape LDS General Conference addresses. Two-source approach:

  1. Pre-1971 (1880–1970): Internet Archive plain-text OCR of scanned Conference Reports.
     URL pattern: https://archive.org/download/conferencereport{year}{session}/
                  conferencereport{year}{session}_djvu.txt
     Each file is a full conference report; we store it as a single session document
     rather than splitting by individual talk (OCR quality makes splitting unreliable).

  2. Post-1971 (1971–2024): churchofjesuschrist.org individual talk pages.
     URL pattern: /study/general-conference/{year}/{month}/{slug}?lang=eng

This corpus serves as the primary "flat control" — no Vatican II analog.
"""

import re
import time
import json
import requests
from pathlib import Path
from bs4 import BeautifulSoup

LDS_BASE = "https://www.churchofjesuschrist.org"
IA_BASE  = "https://archive.org"
OUT = Path(__file__).parent.parent / "data" / "raw" / "lds"
OUT.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Academic research corpus (contact: benedict.r.leonardi@gmail.com)"}

# Internet Archive session identifiers
# April = "a", October = "b"  (some years vary; handled in fetch logic)
IA_START = 1880
IA_END   = 1970

# churchofjesuschrist.org digital archive
CJ_START = 1971
CJ_END   = 2024
MONTHS   = ["04", "10"]


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def fetch(url: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            r = requests.get(url, headers=HEADERS, timeout=45)
            if r.status_code == 200:
                return r.text
            return None
        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    return None


def clean_text(soup: BeautifulSoup) -> str:
    for tag in soup(["script", "style", "nav", "header", "footer", "aside", "figure"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()


# ---------------------------------------------------------------------------
# Phase 1: Internet Archive (pre-1971)
# ---------------------------------------------------------------------------

def ia_identifier(year: int, session: str) -> str:
    """session: 'a' = April/spring, 'b' = October/fall"""
    return f"conferencereport{year}{session}"


def fetch_ia_text(year: int, session: str) -> str | None:
    ident = ia_identifier(year, session)
    url = f"{IA_BASE}/download/{ident}/{ident}_djvu.txt"
    text = fetch(url)
    if text:
        # Strip IA header boilerplate (first ~30 lines often metadata)
        lines = text.split("\n")
        return "\n".join(lines).strip()
    return None


def scrape_ia():
    manifest = []
    # April = "a", October = "sa" (semi-annual) on Internet Archive
    # Some years also used bare year or other conventions — try in order
    SESSIONS = [
        ("04", ["a"]),
        ("10", ["sa", "b", "oct"]),
    ]

    for year in range(IA_START, IA_END + 1):
        for month, suffixes in SESSIONS:
            fname = f"{year}_{month}_ia_conference_report.txt"
            fpath = OUT / fname

            if fpath.exists():
                print(f"  Exists: {fname}")
            else:
                print(f"Fetching IA {year}/{month}...", end=" ", flush=True)
                text = None
                for suffix in suffixes:
                    text = fetch_ia_text(year, suffix)
                    if text:
                        break
                if text and len(text.split()) > 100:
                    fpath.write_text(text, encoding="utf-8", errors="replace")
                    print(f"saved ({len(text.split()):,} words)")
                else:
                    print("not found")
                time.sleep(1.0)

            if fpath.exists():
                manifest.append({
                    "tradition": "lds",
                    "source": "internet_archive",
                    "year": year,
                    "month": month,
                    "title": f"General Conference Report {year} ({'April' if month == '04' else 'October'})",
                    "url": f"{IA_BASE}/details/conferencereport{year}{'a' if month == '04' else 'sa'}",
                    "file": fname,
                    "granularity": "session",
                })

    return manifest


# ---------------------------------------------------------------------------
# Phase 2: churchofjesuschrist.org (1971–2024)
# ---------------------------------------------------------------------------

def session_url(year: int, month: str) -> str:
    return f"{LDS_BASE}/study/general-conference/{year}/{month}?lang=eng"


def get_talk_links(session_html: str, year: int, month: str) -> list[dict]:
    soup = BeautifulSoup(session_html, "html.parser")
    pattern = re.compile(rf"/study/general-conference/{year}/{month}/[^?#\"]+")
    talks, seen = [], set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if pattern.match(href):
            full = LDS_BASE + href.split("?")[0] + "?lang=eng"
            title = a.get_text(strip=True)
            if title and len(title) > 5 and full not in seen:
                seen.add(full)
                talks.append({"url": full, "title": title})
    return talks


def scrape_talk(url: str) -> dict | None:
    html = fetch(url)
    if not html:
        return None
    soup = BeautifulSoup(html, "html.parser")
    speaker = ""
    for sel in [".author-name", "[class*='author']", "p.byline", ".sc-hLseeU"]:
        el = soup.select_one(sel)
        if el:
            speaker = el.get_text(strip=True)
            break
    text = clean_text(soup)
    return {"speaker": speaker, "text": text, "word_count": len(text.split())}


def scrape_cj():
    manifest = []
    for year in range(CJ_START, CJ_END + 1):
        for month in MONTHS:
            print(f"\n--- {year} {month} ---")
            session_html = fetch(session_url(year, month))
            if not session_html:
                print("  No session found")
                continue

            talks = get_talk_links(session_html, year, month)
            print(f"  Found {len(talks)} talks")

            for talk in talks:
                slug = re.sub(r"[^a-z0-9]+", "_", talk["title"].lower())[:60].strip("_")
                fname = f"{year}_{month}_{slug}.txt"
                fpath = OUT / fname

                if fpath.exists():
                    pass
                else:
                    result = scrape_talk(talk["url"])
                    if result:
                        fpath.write_text(result["text"], encoding="utf-8")
                        print(f"  Saved: {fname} ({result['word_count']:,} words)")
                    else:
                        print(f"  FAILED: {talk['url']}")
                    time.sleep(1.0)

                manifest.append({
                    "tradition": "lds",
                    "source": "churchofjesuschrist",
                    "year": year,
                    "month": month,
                    "title": talk["title"],
                    "url": talk["url"],
                    "file": fname,
                    "granularity": "talk",
                })

    return manifest


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def scrape_all():
    print("=== Phase 1: Internet Archive pre-1971 reports ===")
    ia_manifest = scrape_ia()
    print(f"\nIA: {len(ia_manifest)} session reports")

    print("\n=== Phase 2: churchofjesuschrist.org 1971–2024 ===")
    cj_manifest = scrape_cj()
    print(f"\nCJ: {len(cj_manifest)} individual talks")

    manifest = ia_manifest + cj_manifest
    manifest_path = OUT.parent.parent / "corpus" / "lds_manifest.json"
    manifest_path.parent.mkdir(exist_ok=True)
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {manifest_path} ({len(manifest)} total entries)")


if __name__ == "__main__":
    scrape_all()
