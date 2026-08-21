#!/usr/bin/env python3
"""Render the manuscript and site figures from the tables in results/tables/.

Every panel is generated from a committed table, so a figure cannot drift from
the numbers it claims to show. Output goes to both `results/figures/` (PNG, for
the site and the repo) and `manuscript/figures/` (PDF, for LaTeX).

Deterministic: no sampling, no random jitter, fixed sort orders.
"""
from __future__ import annotations

import sys
import textwrap
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt          # noqa: E402
import numpy as np                        # noqa: E402
import pandas as pd                       # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_sources import RESULTS, ROOT, log  # noqa: E402

T, E = RESULTS / "tables", RESULTS / "enrichment"
PNG, PDF = RESULTS / "figures", ROOT / "manuscript" / "figures"

# CoSE palette (matches src/index.css) plus one colour per substrate.
COSE_BLUE, COSE_TEAL = "#3b6ea5", "#3fb6a8"
SUBSTRATE_COLOUR = {"JSC1A": "#3fb6a8", "A11": "#c2483f", "A12": "#b7791f", "A17": "#3b6ea5"}
SUBSTRATE_LABEL = {"JSC1A": "JSC-1A simulant", "A11": "Apollo 11",
                   "A12": "Apollo 12", "A17": "Apollo 17"}
ORDER = ["JSC1A", "A11", "A12", "A17"]

plt.rcParams.update({
    "figure.dpi": 150, "savefig.dpi": 300, "font.size": 8,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.titlesize": 9, "axes.titleweight": "bold", "axes.labelsize": 8,
    "legend.frameon": False, "legend.fontsize": 7,
    "xtick.labelsize": 7, "ytick.labelsize": 7, "savefig.bbox": "tight",
})


def save(fig, name: str):
    """Write the PNG (site) and PDF (LaTeX), without a creation timestamp.

    Matplotlib stamps the current time into PDF and PNG metadata by default,
    which would make every re-run produce different bytes and break
    CHECKSUMS.sha256 even when nothing about the figure changed.
    """
    PNG.mkdir(parents=True, exist_ok=True)
    PDF.mkdir(parents=True, exist_ok=True)
    fig.savefig(PNG / f"{name}.png", metadata={"Software": None})
    fig.savefig(PDF / f"{name}.pdf", metadata={"CreationDate": None, "Producer": None})
    plt.close(fig)
    log(f"  ✓ {name}")


def panel(ax, letter):
    ax.text(-0.22, 1.08, letter, transform=ax.transAxes, fontsize=11, fontweight="bold",
            va="bottom", ha="left")


# --------------------------------------------------------------------------- 1
def fig1_growth():
    leaves = pd.read_csv(T / "leaf_counts_long.csv")
    traits = pd.read_csv(T / "plantcv_traits_long.csv")
    m = pd.read_csv(T / "sample_phenotype_expression_map.csv")
    m = m[m["join_confidence"] != "unlinked"]

    fig, axes = plt.subplots(1, 3, figsize=(9.5, 2.9))

    ax = axes[0]
    for sub in ORDER:
        d = leaves[leaves["substrate"] == sub]
        g = d.groupby("day")["n_leaves"].agg(["mean", "sem", "count"])
        ax.plot(g.index, g["mean"], "-o", ms=3, color=SUBSTRATE_COLOUR[sub],
                label=f"{SUBSTRATE_LABEL[sub]} (n={int(g['count'].max())})")
        ax.fill_between(g.index, g["mean"] - g["sem"], g["mean"] + g["sem"],
                        color=SUBSTRATE_COLOUR[sub], alpha=0.18, lw=0)
    ax.set(xlabel="days from first plate scan", ylabel="leaves visible",
           title="Leaf emergence (ISA-Tab)")
    ax.legend(loc="upper left")
    panel(ax, "a")

    ax = axes[1]
    for sub in ORDER:
        d = traits[traits["substrate"] == sub]
        g = d.groupby("day")["area_mm2"].agg(["mean", "sem", "count"])
        ax.plot(g.index, g["mean"], "-o", ms=3, color=SUBSTRATE_COLOUR[sub],
                label=f"{SUBSTRATE_LABEL[sub]} (n={int(g['count'].max())})")
        ax.fill_between(g.index, g["mean"] - g["sem"], g["mean"] + g["sem"],
                        color=SUBSTRATE_COLOUR[sub], alpha=0.18, lw=0)
    ax.set(xlabel="days from first plate scan", ylabel="rosette area (mm$^2$)",
           yscale="log", title="Rosette expansion (PlantCV)")
    ax.legend(loc="upper left")
    panel(ax, "b")

    ax = axes[2]
    for sub in ORDER:
        d = m[m["substrate"] == sub]
        ax.scatter(d["area_mm2_last"], d["leaf_final"], s=34,
                   color=SUBSTRATE_COLOUR[sub], edgecolor="white", lw=0.6,
                   label=SUBSTRATE_LABEL[sub], zorder=3)
    ax.legend(loc="lower right")
    rho = float(m["qc_leaf_area_spearman"].iloc[0])
    ax.set(xscale="log", xlabel="rosette area, day 8 (mm$^2$)",
           ylabel="leaf count, day 16", title="Two independent phenotypes agree")
    ax.text(0.04, 0.94, f"Spearman $\\rho$ = {rho:.2f}\nn = {len(m)} sequenced plants",
            transform=ax.transAxes, va="top", fontsize=7)
    panel(ax, "c")

    fig.tight_layout()
    save(fig, "fig1_growth_phenotypes")


# --------------------------------------------------------------------------- 2
def fig2_substrate():
    ts = pd.read_csv(T / "substrate_probe_timeseries.csv")
    comp = pd.read_csv(T / "substrate_chemistry_comparison.csv")

    fig, axes = plt.subplots(1, 4, figsize=(12, 2.8))
    subs = sorted(ts["substrate"].unique())
    cmap = plt.get_cmap("tab10")
    colours = {s: cmap(i % 10) for i, s in enumerate(subs)}

    for ax, (col, label) in zip(axes[:3], [("water_content_pct", "water content (%)"),
                                           ("ec_us_cm", "EC (µS/cm)"),
                                           ("ph", "pH")]):
        for s in subs:
            d = ts[ts["substrate"] == s].sort_values("time_min")
            ax.plot(d["time_min"] / 60.0, d[col], lw=1.3, color=colours[s], label=s)
        ax.set(xlabel="hours", ylabel=label)
        if col == "ec_us_cm":
            ax.set_yscale("symlog", linthresh=10)
    axes[0].set_title("Substrate probe: water uptake")
    axes[1].set_title("Ion release")
    axes[2].set_title("Acidity")
    for a, l in zip(axes[:3], "abc"):
        panel(a, l)
    # One shared legend beneath the three probe panels, so no curve is hidden.
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, ncol=len(labels), loc="lower center",
               bbox_to_anchor=(0.38, -0.10), fontsize=6.5, columnspacing=1.2)

    ax = axes[3]
    d = comp.dropna(subset=["lhs1_wt_pct", "ce5_wt_pct"]).sort_values("ce5_wt_pct")
    y = np.arange(len(d))
    ax.barh(y - 0.2, d["lhs1_wt_pct"], height=0.38, color=COSE_TEAL, label="LHS-1 simulant")
    ax.barh(y + 0.2, d["ce5_wt_pct"], height=0.38, color=COSE_BLUE, label="Chang'e-5 soil")
    ax.set_yticks(y, d["oxide"])
    ax.set(xlabel="wt %", title="Simulant vs real lunar soil")
    ax.legend(loc="lower right")
    panel(ax, "d")

    fig.tight_layout()
    save(fig, "fig2_substrate_characterisation")


# --------------------------------------------------------------------------- 3
def fig3_growth_transcriptome():
    res = pd.read_csv(T / "growth_correlated_genes.csv.gz")
    ex = pd.read_csv(T / "expression_examples.csv")

    fig = plt.figure(figsize=(10.5, 6.2))
    gs = fig.add_gridspec(2, 3, height_ratios=[1.15, 1.0], hspace=0.55, wspace=0.42)

    # (a) rho against mean expression: growth-tracking genes are not simply the
    # highly expressed ones, which a rho-vs-p volcano cannot show (with fixed n,
    # p is a deterministic function of |rho|, so that plot is always a U).
    ax = fig.add_subplot(gs[0, 0])
    d = res[(res["analysis"] == "primary") & (res["covariate"] == "leaf_rate_per_day")]
    sig = d["fdr"] < 0.05
    ax.axhline(0, color="#c8cedb", lw=0.8)
    ax.scatter(d.loc[~sig, "mean_vst"], d.loc[~sig, "spearman_rho"], s=2,
               color="#c8cedb", lw=0)
    ax.scatter(d.loc[sig, "mean_vst"], d.loc[sig, "spearman_rho"], s=3,
               color=COSE_BLUE, lw=0)
    ax.set(xlabel="mean VST expression", ylabel="Spearman $\\rho$ vs leaf rate",
           title=f"{int(sig.sum())} genes at FDR 5%")
    panel(ax, "a")

    # (b) the replication check, over *every* gene rather than only the hits.
    ax = fig.add_subplot(gs[0, 1])
    w = (res[res["covariate"] == "leaf_rate_per_day"]
         .pivot_table(index="gene", columns="analysis",
                      values=["spearman_rho", "fdr"]).dropna())
    rho_p, rho_w = w[("spearman_rho", "primary")], w[("spearman_rho", "within_lunar")]
    both = (w[("fdr", "primary")] < 0.05) & (w[("fdr", "within_lunar")] < 0.05) \
        & (np.sign(rho_p) == np.sign(rho_w))
    ax.axhline(0, color="#c8cedb", lw=0.8)
    ax.axvline(0, color="#c8cedb", lw=0.8)
    ax.plot([-1, 1], [-1, 1], color="#c8cedb", lw=0.8, ls=":")
    ax.scatter(rho_p[~both], rho_w[~both], s=2, color="#dfe4ec", lw=0)
    ax.scatter(rho_p[both], rho_w[both], s=6, color=COSE_TEAL, lw=0)
    ax.set(xlabel="$\\rho$, all 16 plants", ylabel="$\\rho$, Apollo only (n=12)",
           xlim=(-1, 1), ylim=(-1, 1),
           title=f"{int(both.sum())} replicate in Apollo only")
    panel(ax, "b")

    # (c) how the two phenotype layers rank the same plants.
    ax = fig.add_subplot(gs[0, 2])
    m = pd.read_csv(T / "sample_phenotype_expression_map.csv")
    m = m[m["join_confidence"] != "unlinked"]
    for sub in ORDER:
        s_ = m[m["substrate"] == sub]
        ax.scatter(s_["leaf_rate_per_day"], s_["rgr_area_per_day"], s=34,
                   color=SUBSTRATE_COLOUR[sub], edgecolor="white", lw=0.6,
                   label=SUBSTRATE_LABEL[sub], zorder=3)
    ax.axhline(0, color="#c8cedb", lw=0.8)
    ax.set(xlabel="leaf rate (leaves day$^{-1}$)",
           ylabel="rosette relative growth rate (day$^{-1}$)",
           title="Growth spans every substrate")
    ax.legend(loc="upper left")
    panel(ax, "c")

    # (d-f) the example genes, one axis each so the fits do not overplot.
    for i, (gene, d) in enumerate(sorted(ex.groupby("gene", sort=True),
                                         key=lambda kv: -abs(kv[1]["spearman_rho"].iloc[0]))):
        ax = fig.add_subplot(gs[1, i])
        for sub in ORDER:
            s_ = d[d["substrate"] == sub]
            ax.scatter(s_["leaf_rate_per_day"], s_["vst"], s=34,
                       color=SUBSTRATE_COLOUR[sub], edgecolor="white", lw=0.6, zorder=3)
        x, y = d["leaf_rate_per_day"].values, d["vst"].values
        b_, a_ = np.polyfit(x, y, 1)
        xs = np.linspace(x.min(), x.max(), 20)
        ax.plot(xs, a_ + b_ * xs, lw=1.2, color="#5a6473", ls="--", zorder=2)
        ax.set(xlabel="leaf rate (leaves day$^{-1}$)", ylabel="VST expression",
               title=f"{d['label'].iloc[0]}  ({gene})")
        ax.text(0.04, 0.94, f"$\\rho$ = {d['spearman_rho'].iloc[0]:+.2f}",
                transform=ax.transAxes, va="top", fontsize=7)
        panel(ax, "def"[i])

    save(fig, "fig3_growth_anchored_transcriptomics")


# --------------------------------------------------------------------------- 4
def fig4_context():
    ov = pd.read_csv(T / "growth_gene_overlap.csv").iloc[0]
    enr = pd.read_csv(E / "goslim_enrichment.csv")
    bl = pd.read_csv(T / "broad_lunar_model.csv")

    fig, axes = plt.subplots(1, 3, figsize=(10, 3.1))

    ax = axes[0]
    bars = {"published\nDEGs": ov["published_degs_any_apollo_vs_jsc1a"],
            "growth-\ncorrelated": ov["growth_correlated_robust"],
            "overlap": ov["overlap"], "growth-\nonly": ov["growth_only"]}
    ax.bar(range(len(bars)), list(bars.values()),
           color=[COSE_BLUE, COSE_TEAL, "#8fa9c6", "#c2483f"])
    ax.set_xticks(range(len(bars)), list(bars), fontsize=6.5)
    ax.set(ylabel="genes", yscale="log", title="What growth-anchoring adds")
    ax.set_xlabel("published DEGs = any Apollo v JSC-1A, adj. p < 0.05", fontsize=6.5)
    for i, v in enumerate(bars.values()):
        ax.text(i, v, f"{int(v)}", ha="center", va="bottom", fontsize=7)
    panel(ax, "a")

    ax = axes[1]
    d = (enr[enr["gene_set"].str.startswith("robust")]
         .nsmallest(10, "p_value").sort_values("fold_enrichment"))
    colour = [COSE_TEAL if g.endswith("up") else COSE_BLUE for g in d["gene_set"]]
    ax.scatter(d["fold_enrichment"], range(len(d)),
               s=18 + 40 * (d["fdr"] < 0.05), c=colour, zorder=3)
    ax.set_yticks(range(len(d)),
                  [textwrap.fill(n, 30) for n in d["go_name"]], fontsize=6.5)
    ax.axvline(1, color="#c8cedb", lw=0.8)
    ax.set(xlabel="fold enrichment", title="GO-slim, robust growth genes")
    ax.text(0.98, 0.03, "large marker: FDR < 0.05\nteal: up with growth · blue: down",
            transform=ax.transAxes, ha="right", va="bottom", fontsize=6)
    panel(ax, "b")

    ax = axes[2]
    d = bl.dropna(subset=["log2fc_lunar_vs_simulant", "padj"]).copy()
    d["y"] = -np.log10(d["padj"].clip(lower=1e-300))
    sig = d["padj"] < 0.05
    ax.scatter(d.loc[~sig, "log2fc_lunar_vs_simulant"], d.loc[~sig, "y"],
               s=2, color="#c8cedb", lw=0)
    ax.scatter(d.loc[sig, "log2fc_lunar_vs_simulant"], d.loc[sig, "y"],
               s=3, color=COSE_BLUE, lw=0)
    ax.set(xlabel="$\\log_2$ FC (all Apollo vs JSC-1A)", ylabel="$-\\log_{10}$ adj. p",
           title=f"Broad Lunar model — {int(sig.sum())} genes at 5%")
    panel(ax, "c")

    fig.tight_layout()
    save(fig, "fig4_context_and_enrichment")


def main() -> int:
    fig1_growth()
    fig2_substrate()
    fig3_growth_transcriptome()
    fig4_context()
    log(f"\n  figures → {PNG} (png) and {PDF} (pdf)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
