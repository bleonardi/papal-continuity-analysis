"""
Interrupted time series (ITS) and diff-in-diff models.

Models:
  1. Within-Catholic ITS at Vatican II (1965) — level + slope change
  2. Within-Catholic ITS at Vatican I (1870) — for comparison
  3. Diff-in-diff: Catholic vs. LDS control, pre/post 1965
  4. Cross-tradition ITS: estimate discontinuity at each tradition's rupture event

Output: analysis/its_results.csv, analysis/did_results.csv
"""

import json
import warnings
import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from pathlib import Path

warnings.filterwarnings("ignore")

DATA = Path(__file__).parent.parent / "data" / "corpus" / "features.csv"
OUT_DIR = Path(__file__).parent.parent / "analysis"
OUT_DIR.mkdir(exist_ok=True)

# Rupture events per tradition (year of structural break)
RUPTURE_EVENTS = {
    "catholic": 1965,       # Vatican II close
    "anglican": 1976,       # women's ordination debate peak (US Episcopal); Lambeth 1978 as alt
    "sbc": 1979,            # Conservative Resurgence begins
    "lds": None,            # no strong rupture candidate — control group
    "orthodox": 1965,       # use same as catholic for parallel test
    "wcc": 1968,            # Uppsala assembly, shift toward social justice framing
}

OUTCOMES = [
    "fk_grade",
    "flesch_ease",
    "type_token_ratio",
    "avg_sentence_length",
    "hedge_rate",
    "fp_plural_rate",
    "theol_juridical_rate",
    "theol_pastoral_rate",
    "theol_ecumenical_rate",
    "theol_modern_world_rate",
    "cosine_sim_to_prev",
]


def build_its_vars(df: pd.DataFrame, cutoff: int) -> pd.DataFrame:
    """Add ITS dummy variables for a given cutoff year."""
    d = df.copy()
    d["post"] = (d["year"] >= cutoff).astype(int)
    d["time"] = d["year"] - cutoff          # centered at cutoff
    d["time_post"] = d["time"] * d["post"]  # slope change post-cutoff
    return d


def run_its(df: pd.DataFrame, outcome: str, cutoff: int,
            tradition: str, controls: list[str] = None) -> dict:
    sub = df[(df["tradition"] == tradition) & df[outcome].notna()].copy()
    if len(sub) < 6:
        return {"tradition": tradition, "outcome": outcome, "cutoff": cutoff,
                "n": len(sub), "note": "insufficient data"}

    sub = build_its_vars(sub, cutoff)
    ctrl_str = " + ".join(controls) if controls else ""
    formula = f"{outcome} ~ time + post + time_post" + (f" + {ctrl_str}" if ctrl_str else "")

    try:
        model = smf.ols(formula, data=sub).fit(cov_type="HC3")
        return {
            "tradition": tradition,
            "outcome": outcome,
            "cutoff": cutoff,
            "n": len(sub),
            "level_change": round(model.params.get("post", np.nan), 4),
            "level_change_se": round(model.bse.get("post", np.nan), 4),
            "level_change_p": round(model.pvalues.get("post", np.nan), 4),
            "slope_change": round(model.params.get("time_post", np.nan), 4),
            "slope_change_se": round(model.bse.get("time_post", np.nan), 4),
            "slope_change_p": round(model.pvalues.get("time_post", np.nan), 4),
            "r2": round(model.rsquared, 4),
        }
    except Exception as e:
        return {"tradition": tradition, "outcome": outcome, "cutoff": cutoff,
                "n": len(sub), "note": str(e)}


def run_did(df: pd.DataFrame, outcome: str, treatment: str,
            control: str, cutoff: int) -> dict:
    """
    Diff-in-diff: treatment tradition vs. control tradition, pre/post cutoff.
    """
    sub = df[df["tradition"].isin([treatment, control]) & df[outcome].notna()].copy()
    if len(sub) < 10:
        return {"treatment": treatment, "control": control, "outcome": outcome,
                "cutoff": cutoff, "n": len(sub), "note": "insufficient data"}

    sub["treated"] = (sub["tradition"] == treatment).astype(int)
    sub["post"] = (sub["year"] >= cutoff).astype(int)
    sub["did"] = sub["treated"] * sub["post"]
    sub["time"] = sub["year"] - cutoff

    formula = f"{outcome} ~ treated + post + did + time + time:treated"
    try:
        model = smf.ols(formula, data=sub).fit(cov_type="HC3")
        return {
            "treatment": treatment,
            "control": control,
            "outcome": outcome,
            "cutoff": cutoff,
            "n": len(sub),
            "did_coef": round(model.params.get("did", np.nan), 4),
            "did_se": round(model.bse.get("did", np.nan), 4),
            "did_p": round(model.pvalues.get("did", np.nan), 4),
            "r2": round(model.rsquared, 4),
        }
    except Exception as e:
        return {"treatment": treatment, "control": control, "outcome": outcome,
                "cutoff": cutoff, "n": len(sub), "note": str(e)}


def run_all():
    if not DATA.exists():
        print(f"Features file not found: {DATA}")
        print("Run extract_features.py first.")
        return

    df = pd.read_csv(DATA)
    print(f"Loaded {len(df)} documents across traditions:")
    print(df.groupby("tradition")["year"].agg(["count", "min", "max"]).to_string())

    # 1. Within-Catholic ITS at Vatican II
    print("\n--- Within-Catholic ITS (Vatican II, 1965) ---")
    its_results = []
    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue
        result = run_its(df, outcome, cutoff=1965, tradition="catholic")
        its_results.append(result)
        if "level_change" in result:
            sig = "**" if result["level_change_p"] < 0.05 else ("*" if result["level_change_p"] < 0.1 else "")
            print(f"  {outcome:35s}  level Δ={result['level_change']:+.4f} (p={result['level_change_p']:.3f}){sig}")

    # 2. Within-Catholic ITS at Vatican I (1870) — for comparison
    # Note: limited data pre-1878 in our corpus; use 1878 as proxy (Leo XIII reform era)
    print("\n--- Within-Catholic ITS (post-Leo XIII reform, 1903) ---")
    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue
        result = run_its(df, outcome, cutoff=1903, tradition="catholic")
        result["label"] = "vatican_i_era"
        its_results.append(result)

    # 3. Cross-tradition ITS
    print("\n--- Cross-tradition ITS at each rupture event ---")
    for tradition, cutoff in RUPTURE_EVENTS.items():
        if cutoff is None:
            continue
        trad_df = df[df["tradition"] == tradition]
        if len(trad_df) < 5:
            continue
        for outcome in ["fk_grade", "avg_sentence_length", "type_token_ratio",
                        "cosine_sim_to_prev", "theol_pastoral_rate", "theol_juridical_rate"]:
            if outcome not in df.columns:
                continue
            result = run_its(df, outcome, cutoff=cutoff, tradition=tradition)
            result["rupture_label"] = tradition
            its_results.append(result)

    # 4. Diff-in-diff: Catholic vs. LDS
    print("\n--- Diff-in-Diff: Catholic vs. LDS (cutoff 1965) ---")
    did_results = []
    for outcome in OUTCOMES:
        if outcome not in df.columns:
            continue
        result = run_did(df, outcome, treatment="catholic", control="lds", cutoff=1965)
        did_results.append(result)
        if "did_coef" in result:
            sig = "**" if result["did_p"] < 0.05 else ("*" if result["did_p"] < 0.1 else "")
            print(f"  {outcome:35s}  DiD={result['did_coef']:+.4f} (p={result['did_p']:.3f}){sig}")

    # Save results
    pd.DataFrame(its_results).to_csv(OUT_DIR / "its_results.csv", index=False)
    pd.DataFrame(did_results).to_csv(OUT_DIR / "did_results.csv", index=False)
    print(f"\nSaved: {OUT_DIR}/its_results.csv, did_results.csv")


if __name__ == "__main__":
    run_all()
