"""
Aggregate all LDS documents by year into a single file per year.
Outputs: data/raw/lds_agg/{year}.txt + data/corpus/lds_agg_manifest.json
"""

import json
import re
from pathlib import Path

RAW     = Path(__file__).parent.parent / "data" / "raw" / "lds"
OUT_DIR = Path(__file__).parent.parent / "data" / "raw" / "lds_agg"
MANIF   = Path(__file__).parent.parent / "data" / "corpus" / "lds_agg_manifest.json"

OUT_DIR.mkdir(parents=True, exist_ok=True)

# Collect all lds txt files, parse year
by_year: dict[int, list[Path]] = {}
for fpath in sorted(RAW.glob("*.txt")):
    m = re.match(r"(\d{4})_", fpath.name)
    if not m:
        continue
    year = int(m.group(1))
    by_year.setdefault(year, []).append(fpath)

manifest = []
for year in sorted(by_year):
    files = sorted(by_year[year])
    parts = []
    for fp in files:
        try:
            parts.append(fp.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            print(f"  Error reading {fp.name}: {e}")

    combined = "\n\n".join(parts)
    out_file = OUT_DIR / f"{year}.txt"
    out_file.write_text(combined, encoding="utf-8")

    manifest.append({
        "tradition": "lds",
        "year": year,
        "title": f"LDS General Conference {year}",
        "file": f"{year}.txt",
        "source_files": len(files),
    })
    print(f"  {year}: {len(files)} files → {len(combined.split()):,} words")

MANIF.write_text(json.dumps(manifest, indent=2))
print(f"\nAggregated {len(manifest)} LDS years → {OUT_DIR}")
print(f"Manifest: {MANIF}")
