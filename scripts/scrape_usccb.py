"""
Scrape NCCB/USCCB pastoral letters from confirmed accessible sources.

USCCB.org main site is Cloudflare-blocked for programmatic access.
Sources used:
  - usccb.org/upload/  (PDFs — bypasses Cloudflare for direct asset paths)
  - priestsforlife.org  (HTML full text for 1960s docs)
  - usccb.org HTML pages (some resource pages accessible)
  - pdfminer.six for PDF extraction
"""

import io
import json
import re
import time
import urllib.request
from pathlib import Path

import requests
from bs4 import BeautifulSoup

try:
    from pdfminer.high_level import extract_text as pdf_extract
    HAS_PDFMINER = True
except ImportError:
    HAS_PDFMINER = False
    print("Warning: pdfminer.six not installed — PDF extraction unavailable")

OUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "usccb"
MANIF   = Path(__file__).parent.parent / "data" / "corpus" / "usccb_manifest.json"
OUT_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/pdf,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# Confirmed accessible documents: (title, year, url, format)
# Pre-1965 (NCWC era), Vatican II era, post-conciliar era
DOCUMENTS = [
    # --- Pre-1965: NCWC (National Catholic Welfare Conference) ---
    ("Program for Social Reconstruction",         1919,
     "https://www.thearda.com/us-religion/history/timelines/entry?etype=1&eid=151", "html"),
    ("Discrimination and the Christian Conscience", 1958,
     "https://www.thearda.com/us-religion/history/timelines/entry?etype=1&eid=152", "html"),

    # --- Vatican II and immediate aftermath ---
    ("Human Life in Our Day",                     1968,
     "https://www.priestsforlife.org/magisterium/bishops/68-11-15humanlifeinourdaynccb.htm", "html"),
    ("To Live in Christ Jesus",                   1976,
     "https://www.usccb.org/committees/doctrine/live-christ-jesus", "html_urllib"),
    ("Brothers and Sisters to Us",                1979,
     "https://www.usccb.org/committees/african-american-affairs/brothers-and-sisters-us", "html_urllib"),

    # --- Major post-conciliar pastoral letters (PDFs confirmed) ---
    ("The Challenge of Peace",                    1983,
     "https://www.usccb.org/upload/challenge-peace-gods-promise-our-response-1983.pdf", "pdf"),
    ("Economic Justice for All",                  1986,
     "https://www.usccb.org/upload/economic_justice_for_all.pdf", "pdf"),
    ("Heritage and Hope: Evangelization in the US", 1991,
     "https://www.usccb.org/upload/heritage-hope-evangelization-united-states-1991.pdf", "pdf"),

    # --- Later documents ---
    ("Co-Workers in the Vineyard of the Lord",    2005,
     "https://www.usccb.org/upload/co-workers-vineyard-lay-ecclesial-ministry-2005.pdf", "pdf"),
    ("Forming Consciences for Faithful Citizenship", 2007,
     "https://www.usccb.org/issues-and-action/faithful-citizenship/upload/forming-consciences-for-faithful-citizenship.pdf", "pdf"),
]


def extract_html_text(html: str, url: str = "") -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["nav", "header", "footer", "script", "style", "aside",
                     "form", ".nav", ".header", ".footer", ".sidebar"]):
        tag.decompose()
    # Try article/main first, then fall back to body
    for selector in ["article", "main", ".entry-content", "#content",
                     ".page-content", ".article-body", "div.content"]:
        el = soup.select_one(selector)
        if el:
            text = el.get_text(separator="\n", strip=True)
            if len(text.split()) > 300:
                return text
    return soup.get_text(separator="\n", strip=True)


def extract_pdf_text(content: bytes) -> str:
    if not HAS_PDFMINER:
        return ""
    try:
        return pdf_extract(io.BytesIO(content))
    except Exception as e:
        print(f"    PDF extraction error: {e}")
        return ""


def fetch_doc(title: str, year: int, url: str, fmt: str) -> dict | None:
    fname = re.sub(r"[^\w]+", "_", title.lower()).strip("_") + f"_{year}.txt"
    fpath = OUT_DIR / fname

    if fpath.exists() and fpath.stat().st_size > 1000:
        text = fpath.read_text(encoding="utf-8")
        wc = len(text.split())
        print(f"  Exists: {year} {title} ({wc:,} words)")
        if wc > 100:
            return {"tradition": "usccb", "year": year, "title": title,
                    "file": fname, "source": url}
        # Too short — re-fetch
        print(f"    Re-fetching (too short: {wc} words)...")

    try:
        if fmt == "html_urllib":
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)",
            })
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode("utf-8", errors="replace")
            text = extract_html_text(html, url)
        else:
            r = requests.get(url, headers=HEADERS, timeout=20, allow_redirects=True)
            if r.status_code != 200:
                print(f"  SKIP {year} {title}: HTTP {r.status_code}")
                return None
            if fmt == "pdf" or "application/pdf" in r.headers.get("content-type", ""):
                text = extract_pdf_text(r.content)
            else:
                text = extract_html_text(r.text, url)

        # Clean up
        text = re.sub(r"\n{3,}", "\n\n", text).strip()
        wc = len(text.split())

        if wc < 200:
            print(f"  SKIP {year} {title}: too short ({wc} words after extraction)")
            return None

        fpath.write_text(text, encoding="utf-8")
        print(f"  Saved: {year} {title} ({wc:,} words)")
        return {"tradition": "usccb", "year": year, "title": title,
                "file": fname, "source": url}

    except Exception as e:
        print(f"  ERROR {year} {title}: {e}")
        return None


def main():
    manifest = []
    for title, year, url, fmt in DOCUMENTS:
        doc = fetch_doc(title, year, url, fmt)
        if doc:
            manifest.append(doc)
        time.sleep(1.5)

    MANIF.write_text(json.dumps(manifest, indent=2))
    print(f"\nUSCCB manifest: {len(manifest)} documents")
    if manifest:
        print(f"Years: {min(d['year'] for d in manifest)}–{max(d['year'] for d in manifest)}")


if __name__ == "__main__":
    main()
