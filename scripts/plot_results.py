"""
Generate plots for the papal continuity analysis.

Figures produced:
  1. fk_grade_by_tradition.png    — FK grade over time, all traditions
  2. sentence_length_catholic.png — avg sentence length with ITS fit lines
  3. cosine_sim_catholic.png      — cosine similarity to predecessor (Catholic)
  4. cosine_sim_all.png           — cosine similarity, all traditions
  5. theological_vocab.png        — theological cluster rates over time (Catholic)
  6. cross_tradition_its.png      — ITS level-change estimates compared across traditions
"""

import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from pathlib import Path

DATA   = Path(__file__).parent.parent / "data" / "corpus" / "features.csv"
ITS    = Path(__file__).parent.parent / "analysis" / "its_results.csv"
OUT    = Path(__file__).parent.parent / "analysis"
OUT.mkdir(exist_ok=True)

TRADITION_COLORS = {
    "catholic": "#c0392b",
    "lds":      "#2980b9",
    "sbc":      "#27ae60",
    "anglican": "#8e44ad",
    "orthodox": "#e67e22",
    "usccb":    "#16a085",
}

TRADITION_LABELS = {
    "catholic": "Catholic (encyclicals)",
    "lds":      "LDS (conference reports/talks)",
    "sbc":      "SBC (resolutions)",
    "anglican": "Anglican (Lambeth)",
    "orthodox": "Orthodox (curated)",
    "usccb":    "USCCB (pastoral letters)",
}

plt.rcParams.update({
    "figure.dpi": 150,
    "font.family": "sans-serif",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.3,
    "grid.linestyle": "--",
})

df = pd.read_csv(DATA)
its = pd.read_csv(ITS) if ITS.exists() else pd.DataFrame()

VII = 1965
VATII_COLOR = "#999999"


def vline(ax, x=VII, label="Vatican II (1965)"):
    ax.axvline(x, color=VATII_COLOR, lw=1.5, ls="--", alpha=0.8)
    ax.text(x + 0.5, ax.get_ylim()[1] * 0.97, label,
            fontsize=7, color=VATII_COLOR, va="top")


def rolling_mean(series_x, series_y, window=5):
    tmp = pd.DataFrame({"x": series_x, "y": series_y}).sort_values("x")
    return tmp["x"], tmp["y"].rolling(window, center=True, min_periods=2).mean()


# ---------------------------------------------------------------------------
# Fig 1: FK grade over time by tradition (excl. SBC — too short)
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5))
for trad in ["catholic", "lds", "anglican", "orthodox"]:
    sub = df[(df.tradition == trad) & df.fk_grade.notna()].copy()
    if sub.empty:
        continue
    ax.scatter(sub.year, sub.fk_grade, s=8, alpha=0.25,
               color=TRADITION_COLORS[trad])
    rx, ry = rolling_mean(sub.year, sub.fk_grade, window=5)
    ax.plot(rx, ry, lw=2, color=TRADITION_COLORS[trad],
            label=TRADITION_LABELS[trad])

# USCCB — full pastoral letters only (≥2000 words, 1968+)
usccb = df[(df.tradition == "usccb") & df.fk_grade.notna() &
           (df.year >= 1968) & (df.word_count >= 2000)].sort_values("year")
if not usccb.empty:
    ax.scatter(usccb.year, usccb.fk_grade, s=40, zorder=5,
               color=TRADITION_COLORS["usccb"], marker="D")
    ax.plot(usccb.year, usccb.fk_grade, lw=1.5, ls="--",
            color=TRADITION_COLORS["usccb"], label=TRADITION_LABELS["usccb"])

vline(ax)
ax.set_xlabel("Year")
ax.set_ylabel("Flesch-Kincaid Grade Level")
ax.set_title("Reading Complexity Over Time by Tradition")
ax.legend(fontsize=8)
ax.set_xlim(1860, 2030)
fig.tight_layout()
fig.savefig(OUT / "fk_grade_by_tradition.png")
plt.close()
print("Saved: fk_grade_by_tradition.png")


# ---------------------------------------------------------------------------
# Fig 2: Catholic sentence length with ITS fit lines
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
cat = df[(df.tradition == "catholic") & df.avg_sentence_length.notna()].sort_values("year")

ax.scatter(cat.year, cat.avg_sentence_length, s=20, alpha=0.5,
           color=TRADITION_COLORS["catholic"], zorder=3)

# Fit OLS lines pre/post 1965
for label, sub in [("Pre-Vatican II", cat[cat.year < VII]),
                   ("Post-Vatican II", cat[cat.year >= VII])]:
    if len(sub) < 3:
        continue
    coef = np.polyfit(sub.year, sub.avg_sentence_length, 1)
    xr = np.linspace(sub.year.min(), sub.year.max(), 100)
    ax.plot(xr, np.polyval(coef, xr), lw=2.5,
            color=TRADITION_COLORS["catholic"],
            ls="-" if "Pre" in label else "--", label=label)

vline(ax)
ax.set_xlabel("Year")
ax.set_ylabel("Average Sentence Length (words)")
ax.set_title("Catholic Encyclicals: Sentence Length 1878–2024")
ax.legend(fontsize=9)
fig.tight_layout()
fig.savefig(OUT / "sentence_length_catholic.png")
plt.close()
print("Saved: sentence_length_catholic.png")


# ---------------------------------------------------------------------------
# Fig 3: Cosine similarity to predecessor — Catholic
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(9, 5))
cat_sim = cat[cat.cosine_sim_to_prev.notna()].copy()
ax.scatter(cat_sim.year, cat_sim.cosine_sim_to_prev, s=20, alpha=0.5,
           color=TRADITION_COLORS["catholic"], zorder=3)
rx, ry = rolling_mean(cat_sim.year, cat_sim.cosine_sim_to_prev, window=5)
ax.plot(rx, ry, lw=2.5, color=TRADITION_COLORS["catholic"], label="5-doc rolling mean")

vline(ax)
ax.set_xlabel("Year")
ax.set_ylabel("Cosine Similarity to Previous Encyclical")
ax.set_title("Catholic Encyclicals: Textual Continuity with Predecessor")
ax.legend(fontsize=9)
ax.set_ylim(0, 1)
fig.tight_layout()
fig.savefig(OUT / "cosine_sim_catholic.png")
plt.close()
print("Saved: cosine_sim_catholic.png")


# ---------------------------------------------------------------------------
# Fig 4: Cosine similarity — all traditions
# ---------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(11, 5))
for trad in ["catholic", "lds", "anglican", "orthodox"]:
    sub = df[(df.tradition == trad) & df.cosine_sim_to_prev.notna()].copy()
    if len(sub) < 3:
        continue
    rx, ry = rolling_mean(sub.year, sub.cosine_sim_to_prev, window=5)
    ax.plot(rx, ry, lw=2, color=TRADITION_COLORS[trad],
            label=TRADITION_LABELS[trad])
    ax.scatter(sub.year, sub.cosine_sim_to_prev, s=6, alpha=0.2,
               color=TRADITION_COLORS[trad])

vline(ax)
ax.set_xlabel("Year")
ax.set_ylabel("Cosine Similarity to Previous Document")
ax.set_title("Textual Continuity Over Time: All Traditions")
ax.legend(fontsize=8)
ax.set_ylim(0, 1)
ax.set_xlim(1860, 2030)
fig.tight_layout()
fig.savefig(OUT / "cosine_sim_all.png")
plt.close()
print("Saved: cosine_sim_all.png")


# ---------------------------------------------------------------------------
# Fig 5: Theological vocabulary clusters — Catholic
# ---------------------------------------------------------------------------
clusters = ["theol_juridical_rate", "theol_pastoral_rate",
            "theol_ecumenical_rate", "theol_modern_world_rate"]
cluster_labels = ["Juridical", "Pastoral", "Ecumenical", "Modern World"]
cluster_colors = ["#c0392b", "#27ae60", "#2980b9", "#e67e22"]

fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True)
for ax, col, label, color in zip(axes.flat, clusters, cluster_labels, cluster_colors):
    sub = cat[cat[col].notna()]
    ax.scatter(sub.year, sub[col] * 1000, s=12, alpha=0.4, color=color)
    rx, ry = rolling_mean(sub.year, sub[col] * 1000, window=5)
    ax.plot(rx, ry, lw=2, color=color)
    ax.axvline(VII, color=VATII_COLOR, lw=1.2, ls="--", alpha=0.7)
    ax.set_title(f"{label} vocabulary rate (per 1,000 words)")
    ax.set_ylabel("Rate")

for ax in axes[1]:
    ax.set_xlabel("Year")
fig.suptitle("Catholic Encyclicals: Theological Vocabulary by Cluster", fontsize=13)
fig.tight_layout()
fig.savefig(OUT / "theological_vocab.png")
plt.close()
print("Saved: theological_vocab.png")


# ---------------------------------------------------------------------------
# Fig 6: Cross-tradition ITS level-change comparison
# ---------------------------------------------------------------------------
if not its.empty and "level_change" in its.columns:
    outcomes_to_plot = ["fk_grade", "avg_sentence_length", "cosine_sim_to_prev"]
    its_sub = its[
        its.outcome.isin(outcomes_to_plot) &
        its.level_change.notna() &
        ~its.get("label", pd.Series(dtype=str)).isin(["vatican_i_era"])
    ].copy()

    if not its_sub.empty:
        fig, axes = plt.subplots(1, len(outcomes_to_plot), figsize=(13, 5))
        for ax, outcome in zip(axes, outcomes_to_plot):
            sub = its_sub[its_sub.outcome == outcome].copy()
            if sub.empty:
                continue
            trads = sub.tradition.tolist()
            vals  = sub.level_change.tolist()
            errs  = sub.level_change_se.tolist()
            colors = [TRADITION_COLORS.get(t, "#555") for t in trads]
            y_pos = range(len(trads))
            ax.barh(y_pos, vals, xerr=errs, color=colors, alpha=0.8,
                    error_kw={"capsize": 4, "elinewidth": 1.2})
            ax.axvline(0, color="black", lw=0.8)
            ax.set_yticks(list(y_pos))
            ax.set_yticklabels(trads, fontsize=8)
            ax.set_title(outcome.replace("_", " ").title(), fontsize=10)
            ax.set_xlabel("Level change at rupture event")

        fig.suptitle("ITS Level-Change Estimates at Each Tradition's Rupture Event",
                     fontsize=12)
        fig.tight_layout()
        fig.savefig(OUT / "cross_tradition_its.png")
        plt.close()
        print("Saved: cross_tradition_its.png")
    else:
        print("cross_tradition_its: insufficient ITS data to plot")

# ---------------------------------------------------------------------------
# Fig 7: USCCB vs Catholic — post-VII trend comparison
# ---------------------------------------------------------------------------
fig, axes = plt.subplots(1, 3, figsize=(14, 5))
metrics = ["fk_grade", "avg_sentence_length", "cosine_sim_to_prev"]
ylabels = ["Flesch-Kincaid Grade", "Avg Sentence Length (words)", "Cosine Sim to Predecessor"]

cat_post = df[(df.tradition == "catholic") & (df.year >= 1965)].sort_values("year")
usccb    = df[(df.tradition == "usccb") & (df.year >= 1968) & (df.word_count >= 2000)].sort_values("year")

for ax, metric, ylabel in zip(axes, metrics, ylabels):
    # Catholic post-VII rolling mean
    cat_v = cat_post[cat_post[metric].notna()]
    if not cat_v.empty:
        rx, ry = rolling_mean(cat_v.year, cat_v[metric], window=5)
        ax.plot(rx, ry, lw=2.5, color=TRADITION_COLORS["catholic"],
                label="Catholic encyclicals")
        ax.scatter(cat_v.year, cat_v[metric], s=8, alpha=0.25,
                   color=TRADITION_COLORS["catholic"])

    # USCCB dots + line
    usccb_v = usccb[usccb[metric].notna()]
    if not usccb_v.empty:
        ax.scatter(usccb_v.year, usccb_v[metric], s=60, zorder=5,
                   color=TRADITION_COLORS["usccb"], marker="D",
                   label="USCCB pastoral letters")
        ax.plot(usccb_v.year, usccb_v[metric], lw=1.5, ls="--",
                color=TRADITION_COLORS["usccb"])

    ax.axvline(1965, color=VATII_COLOR, lw=1.2, ls="--", alpha=0.7)
    ax.set_xlabel("Year")
    ax.set_ylabel(ylabel)
    ax.legend(fontsize=8)

fig.suptitle("Post-Vatican II: Catholic Encyclicals vs. USCCB Pastoral Letters", fontsize=12)
fig.tight_layout()
fig.savefig(OUT / "usccb_vs_catholic.png")
plt.close()
print("Saved: usccb_vs_catholic.png")

print("\nAll plots saved to analysis/")
