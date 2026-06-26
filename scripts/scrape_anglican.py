"""
Scrape Anglican Lambeth Conference resolutions.

Sources:
  1867–1998: PDFs at anglicancommunion.org/wp-content/uploads/2026/02/{year}.pdf
  2008+:     lambethconference.org (different site, HTML)
  1867–1888: Also available as IA full text (backup)

Text extracted from PDFs using pdfminer.six.
"""

import re
import io
import time
import json
import requests
from pathlib import Path

OUT = Path(__file__).parent.parent / "data" / "raw" / "anglican"
OUT.mkdir(parents=True, exist_ok=True)
CORPUS_DIR = Path(__file__).parent.parent / "data" / "corpus"
CORPUS_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

# Confirmed PDF URLs at anglicancommunion.org
PDF_CONFERENCES = [
    (1867, "https://anglicancommunion.org/wp-content/uploads/2026/02/1867.pdf"),
    (1878, "https://anglicancommunion.org/wp-content/uploads/2026/02/1878.pdf"),
    (1888, "https://anglicancommunion.org/wp-content/uploads/2026/02/1888.pdf"),
    (1897, "https://anglicancommunion.org/wp-content/uploads/2026/02/1897.pdf"),
    (1908, "https://anglicancommunion.org/wp-content/uploads/2026/02/1908.pdf"),
    (1920, "https://anglicancommunion.org/wp-content/uploads/2026/02/1920.pdf"),
    (1930, "https://anglicancommunion.org/wp-content/uploads/2026/02/1930.pdf"),
    (1948, "https://anglicancommunion.org/wp-content/uploads/2026/02/1948.pdf"),
    (1958, "https://anglicancommunion.org/wp-content/uploads/2026/02/1958.pdf"),
    (1968, "https://anglicancommunion.org/wp-content/uploads/2026/02/1968.pdf"),
    (1978, "https://anglicancommunion.org/wp-content/uploads/2026/02/1978.pdf"),
    (1988, "https://anglicancommunion.org/wp-content/uploads/2026/02/1988.pdf"),
    (1998, "https://anglicancommunion.org/wp-content/uploads/2026/02/1998.pdf"),
]

# 2008 and 2022 need separate handling
HTML_CONFERENCES = [
    (2008, "https://www.lambethconference.org/resolutions/"),
    (2022, "https://www.lambethconference.org/lambeth-calls/"),
]

# Internet Archive backup for earliest conferences
IA_BACKUP = {
    1867: "https://archive.org/download/a589564000lambuoft/a589564000lambuoft_djvu.txt",
}


def fetch_bytes(url: str) -> bytes | None:
    for attempt in range(3):
        try:
            r = requests.get(url, headers=HEADERS, timeout=60)
            if r.status_code == 200:
                return r.content
            print(f"  HTTP {r.status_code}: {url}")
            return None
        except Exception as e:
            print(f"  Error (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt)
    return None


def fetch_text(url: str) -> str | None:
    content = fetch_bytes(url)
    if content:
        try:
            return content.decode("utf-8", errors="replace")
        except Exception:
            return None
    return None


def pdf_to_text(pdf_bytes: bytes) -> str:
    try:
        from pdfminer.high_level import extract_text
        text = extract_text(io.BytesIO(pdf_bytes))
        return re.sub(r"\s+", " ", text).strip()
    except Exception as e:
        print(f"  pdfminer error: {e}")
        return ""


def scrape_html_conference(year: int, url: str) -> str:
    from bs4 import BeautifulSoup
    text = fetch_text(url)
    if not text:
        return ""
    soup = BeautifulSoup(text, "html.parser")
    for tag in soup(["script", "style", "nav", "header", "footer", "aside"]):
        tag.decompose()
    return re.sub(r"\s+", " ", soup.get_text(separator=" ")).strip()


def scrape_all():
    manifest = []

    # Phase 1: PDF conferences 1867–1998
    print("=== PDF conferences (1867–1998) ===")
    for year, url in PDF_CONFERENCES:
        fname = f"{year}_lambeth_conference_resolutions.txt"
        fpath = OUT / fname

        if fpath.exists() and fpath.stat().st_size > 500:
            print(f"  Exists: {fname}")
        else:
            print(f"Fetching {year} PDF...", end=" ", flush=True)
            pdf_bytes = fetch_bytes(url)
            if pdf_bytes:
                text = pdf_to_text(pdf_bytes)
                if len(text.split()) > 100:
                    fpath.write_text(text, encoding="utf-8")
                    print(f"saved ({len(text.split()):,} words)")
                else:
                    # Fallback to IA if PDF extraction fails
                    if year in IA_BACKUP:
                        print(f"trying IA backup...", end=" ", flush=True)
                        ia_text = fetch_text(IA_BACKUP[year])
                        if ia_text and len(ia_text.split()) > 100:
                            fpath.write_text(ia_text, encoding="utf-8")
                            print(f"saved via IA ({len(ia_text.split()):,} words)")
                        else:
                            print("failed")
                    else:
                        print(f"extraction too short ({len(text.split())} words)")
            else:
                print("download failed")
            time.sleep(1.5)

        if fpath.exists():
            manifest.append({
                "tradition": "anglican",
                "year": year,
                "title": f"Lambeth Conference {year} Resolutions",
                "url": url,
                "file": fname,
                "document_type": "lambeth_resolution",
                "source": "anglicancommunion.org PDF",
            })

    # Phase 2: HTML conferences 2008, 2022
    print("\n=== HTML conferences (2008, 2022) ===")
    for year, url in HTML_CONFERENCES:
        fname = f"{year}_lambeth_conference_resolutions.txt"
        fpath = OUT / fname

        if fpath.exists() and fpath.stat().st_size > 500:
            print(f"  Exists: {fname}")
        else:
            print(f"Fetching {year} HTML...", end=" ", flush=True)
            text = scrape_html_conference(year, url)
            if len(text.split()) > 100:
                fpath.write_text(text, encoding="utf-8")
                print(f"saved ({len(text.split()):,} words)")
            else:
                print(f"too short or failed")
            time.sleep(1.5)

        if fpath.exists():
            manifest.append({
                "tradition": "anglican",
                "year": year,
                "title": f"Lambeth Conference {year} Resolutions",
                "url": url,
                "file": fname,
                "document_type": "lambeth_resolution",
                "source": "lambethconference.org HTML",
            })

    manifest_path = CORPUS_DIR / "anglican_manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\nManifest: {manifest_path} ({len(manifest)} conferences)")


if __name__ == "__main__":
    scrape_all()
