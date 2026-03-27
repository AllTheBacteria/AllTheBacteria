#!/usr/bin/env python3
"""
allelome_publication_plots.py  (v2 — adapted to ATB file formats)

Nature/Science-level publication figures from ATB WhatsGNU allelome results.

Input files:
  FROM allelome_plots_v5_v2.py:
    --tables_dir    → reads NEW5, 03, 05, 07 TSVs
    --cache_npz     → 242M allele GNU array

  USER-PROVIDED:
    --samples_tsv        → SampleID  Sample  SpeciesID  Species  HQ
    --species_stats_tsv  → SpeciesID  Species  n_samples  n_HQ_T  n_HQ_F
    --records_per_faa    → sample_name  record_count
    --records_per_species→ species_id  species_name  total_records

Plots:
  1. Alleles vs Genomes scatter (top N labeled, genus-colored)
  2. GNU distribution bar (exact bins from cache)
  3. Coverage bar (total / 0.99 / 0.90 per species)
  4. Shared-alleles heatmap (top N, no Unknown)
  5. Species sharing network (force-directed)
  6. Protein count (proxy for genome size) vs alleles vs genomes (dual-panel,
     one with median, one with mean)
  7. Rank-abundance + singleton fraction inset
  8. Protein count distribution per species (violin/swarm, like GC plots)
"""

from __future__ import annotations

import argparse
import sys
import warnings
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from matplotlib.lines import Line2D
import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", category=UserWarning)

# ── Publication style ─────────────────────────────────────────────────
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["Arial", "Helvetica", "DejaVu Sans"],
    "font.size": 8,
    "axes.titlesize": 10,
    "axes.labelsize": 9,
    "xtick.labelsize": 7,
    "ytick.labelsize": 7,
    "legend.fontsize": 7,
    "figure.dpi": 150,
    "savefig.dpi": 300,
    "savefig.bbox": "tight",
    "axes.linewidth": 0.6,
    "xtick.major.width": 0.5,
    "ytick.major.width": 0.5,
    "axes.spines.top": False,
    "axes.spines.right": False,
    "lines.linewidth": 1.0,
    "patch.linewidth": 0.3,
})

PALETTE = [
    "#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F",
    "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85",
    "#E7B800", "#FC4E07", "#00AFBB", "#868686", "#CD534C",
    "#0073C2", "#EFC000", "#A73030", "#003C67", "#79AF97",
    "#6A6599", "#D5B60A", "#374E55", "#DF8F44", "#AA4499",
    "#882255", "#44AA99", "#999933", "#661100", "#117733",
]


def save(fig, path, dpi=300):
    fig.savefig(path, dpi=dpi, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    print(f"  -> {path}", file=sys.stderr)


def abbrev(sp):
    """'Salmonella enterica' -> 'S. enterica', handles underscores."""
    parts = sp.replace("_", " ").split()
    if len(parts) >= 2:
        return f"{parts[0][0]}. {' '.join(parts[1:])}"
    return sp



def _get_distinct_colors(n):
    """
    Return n visually distinct colors using tab20/tab20b/tab20c.
    Deterministic order so colors are consistent across figures.
    """
    import matplotlib.cm as cm
    cols = []
    for cmap_name in ["tab20", "tab20b", "tab20c"]:
        cmap = cm.get_cmap(cmap_name)
        cols.extend([cmap(i) for i in range(cmap.N)])
    if n <= len(cols):
        return cols[:n]
    # Fallback: cycle if someone requests more than we have
    return [cols[i % len(cols)] for i in range(n)]


def _top_species_color_map(df, species_col, rank_col, top_n=30):
    """
    Build (top_species_list, color_map) where top_species_list is ordered
    by descending rank_col.
    """
    tmp = df[[species_col, rank_col]].dropna().drop_duplicates()
    tmp = tmp.sort_values(rank_col, ascending=False)
    top_species = tmp[species_col].head(top_n).tolist()
    colors = _get_distinct_colors(len(top_species))
    return top_species, dict(zip(top_species, colors))


def _annotate_spiral_no_overlap(ax, xs, ys, labels, fontsize=5.5,
                               italic=True, color="#333333",
                               max_iter=250, step_px=2.5):
    """
    Simple label repulsion for <= ~50 labels:
    place labels near points, then nudge in a spiral in display-coordinates
    until their bounding boxes stop overlapping.
    Works for linear/log axes.
    """
    fig = ax.figure
    texts = []
    for x, y, lab in zip(xs, ys, labels):
        t = ax.annotate(
            lab, xy=(x, y), xytext=(4, 2), textcoords="offset points",
            ha="left", va="bottom",
            fontsize=fontsize,
            fontstyle=("italic" if italic else "normal"),
            color=color,
            annotation_clip=True,
            arrowprops=dict(arrowstyle="-", lw=0.3, color=color, alpha=0.5),
        )
        texts.append(t)

    # Need a renderer to compute bboxes
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()

    def overlaps(b1, b2):
        return b1.overlaps(b2)

    placed = []
    for i, t in enumerate(texts):
        # Spiral search for a free spot
        dx = dy = 0.0
        angle = 0.0
        radius = 0.0
        for it in range(max_iter):
            fig.canvas.draw()
            bb = t.get_window_extent(renderer=renderer).expanded(1.05, 1.10)
            if all(not overlaps(bb, pbb) for pbb in placed):
                placed.append(bb)
                break
            # move text a bit along a spiral
            radius += step_px / (2 * 3.14159)
            angle += 0.7  # radians
            dx = radius * np.cos(angle)
            dy = radius * np.sin(angle)
            t.set_position((4 + dx, 2 + dy))
        else:
            # give up, still add its last bbox
            fig.canvas.draw()
            placed.append(t.get_window_extent(renderer=renderer))
    return texts


def genus_of(sp):
    return sp.replace("_", " ").split()[0]


# ======================================================================
# DATA LOADING
# ======================================================================
def load_samples(path):
    """Load samples_with_ids.tsv -> DataFrame."""
    df = pd.read_csv(path, sep="\t")
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl == "sampleid":
            col_map[c] = "genome_id"
        elif cl == "sample":
            col_map[c] = "sample_name"
        elif cl == "speciesid":
            col_map[c] = "species_id"
        elif cl == "species":
            col_map[c] = "species"
    df = df.rename(columns=col_map)
    return df


def load_species_stats(path):
    """Load species_stats.tsv -> DataFrame sorted by n_samples desc."""
    df = pd.read_csv(path, sep="\t")
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl == "speciesid":
            col_map[c] = "species_id"
        elif cl == "species":
            col_map[c] = "species"
        elif cl == "n_samples":
            col_map[c] = "n_genomes"
        elif cl == "n_hq_t":
            col_map[c] = "n_hq"
    df = df.rename(columns=col_map)
    if "n_genomes" not in df.columns:
        for cand in ["n_samples", "genomes", "count"]:
            if cand in df.columns:
                df = df.rename(columns={cand: "n_genomes"})
                break
    return df.sort_values("n_genomes", ascending=False).reset_index(drop=True)


def load_records_per_faa(path):
    """Load records_per_faa.tsv -> DataFrame: sample_name, record_count."""
    df = pd.read_csv(path, sep="\t")
    col_map = {}
    for c in df.columns:
        cl = c.lower().strip()
        if cl in ("sample_name", "sample", "accession", "genome"):
            col_map[c] = "sample_name"
        elif cl in ("record_count", "n_proteins", "count", "records"):
            col_map[c] = "n_proteins"
    df = df.rename(columns=col_map)
    return df


def join_faa_with_species(faa_df, samples_df):
    """Join records_per_faa with samples to get species per genome."""
    merged = faa_df.merge(
        samples_df[["sample_name", "species_id", "species"]],
        on="sample_name", how="inner")
    return merged


# ======================================================================
# PLOT 1 -- Alleles vs Genomes scatter
# ======================================================================

def plot1_alleles_vs_genomes(summary_df, selected_species, top_n_label,
                             figs, dpi, top_n_color=30):
    """Scatter: x=n_genomes, y=n_alleles. Two versions: log and linear y.

    Styling:
      - Top N species (by genome count) get distinct colors + legend.
      - All other species are gray.
      - Labels are placed for top_n_label species with simple repulsion.
    """
    print("[plot1] Alleles vs Genomes scatter", file=sys.stderr)
    df = summary_df.copy()
    if selected_species is not None:
        df = df[df["species"].isin(selected_species)]
    if df.empty:
        print("  SKIP: no matching species", file=sys.stderr)
        return

    df = df.sort_values("n_genomes_in_species", ascending=False)

    # Color top species by genome sampling depth
    top_species, sp2col = _top_species_color_map(
        df, species_col="species", rank_col="n_genomes_in_species",
        top_n=top_n_color
    )
    is_top = df["species"].isin(set(top_species)).values

    sizes = np.sqrt(df["n_genomes_in_species"].values) * 0.3
    sizes = np.clip(sizes, 8, 200)

    for yscale, suffix in [("log", "log"), ("linear", "linear")]:
        fig, ax = plt.subplots(figsize=(8, 6))
        ax.set_xscale("log")
        if yscale == "log":
            ax.set_yscale("log")

        # Others (gray)
        if (~is_top).any():
            ax.scatter(df.loc[~is_top, "n_genomes_in_species"],
                       df.loc[~is_top, "n_alleles_in_species"],
                       s=sizes[~is_top], c="#BDBDBD", alpha=0.45,
                       edgecolors="white", linewidth=0.25, zorder=2,
                       label="Other species")

        # Top species (colored)
        if is_top.any():
            top_df = df.loc[is_top].copy()
            top_colors = [sp2col[s] for s in top_df["species"]]
            top_sizes = sizes[is_top]
            ax.scatter(top_df["n_genomes_in_species"], top_df["n_alleles_in_species"],
                       s=top_sizes, c=top_colors, alpha=0.80,
                       edgecolors="white", linewidth=0.35, zorder=3)

        # Label top_n_label (subset of top species)
        label_df = df.head(top_n_label)
        xs = label_df["n_genomes_in_species"].values
        ys = label_df["n_alleles_in_species"].values
        labs = [abbrev(s) for s in label_df["species"].values]
        #_annotate_spiral_no_overlap(ax, xs, ys, labs, fontsize=5.5)

        ax.set_xlabel("Number of genomes")
        ax.set_ylabel("Number of unique alleles")
        ax.set_title("Allelic diversity vs genome sampling depth by species")

        # Bubble size legend (genome count)
        size_handles = []
        for s, label in [(500, "<500"), (5000, "5K"), (50000, "50K"),
                         (500000, ">500K")]:
            h = ax.scatter([], [], s=np.sqrt(s) * 0.3, c="gray", alpha=0.5,
                           edgecolors="white", linewidth=0.25, label=label)
            size_handles.append(h)
        size_leg = ax.legend(handles=size_handles, title="Genome count",
                             loc="lower right", framealpha=0.85,
                             scatterpoints=1, fontsize=6, title_fontsize=7)
        ax.add_artist(size_leg)

        # Color legend (top species)
        from matplotlib.lines import Line2D
        color_handles = [Line2D([0], [0], marker='o', linestyle='',
                                markerfacecolor=sp2col[sp], markeredgecolor="white",
                                markeredgewidth=0.4, markersize=5,
                                label=abbrev(sp))
                         for sp in top_species]
        color_handles.append(
            Line2D([0], [0], marker='o', linestyle='', markerfacecolor="#BDBDBD",
                   markeredgecolor="white", markeredgewidth=0.4,
                   markersize=5, label="Other species")
        )
        ax.legend(handles=color_handles, title=f"Top {len(top_species)} species",
                  loc="upper left", bbox_to_anchor=(1.02, 1.0),
                  framealpha=0.85, fontsize=6, title_fontsize=7,
                  ncol=2, borderaxespad=0.0, columnspacing=0.8,
                  handletextpad=0.4, labelspacing=0.35)

        save(fig, figs / f"pub_01_alleles_vs_genomes_{suffix}.png", dpi)


# ======================================================================
# PLOT 2 -- GNU distribution bar plot
# ======================================================================
def plot2_gnu_distribution(tbls, figs, dpi, cache_npz=None):
    """Bar plot of allele counts in GNU score bins."""
    print("[plot2] GNU distribution bar", file=sys.stderr)

    thresholds = [1, 2, 3, 4, 5, 10, 50, 100, 500, 1000, 5000, 10000,
                  50000, 100000]

    if cache_npz and Path(cache_npz).exists():
        z = np.load(cache_npz, allow_pickle=False)
        gnu = z["gnu"]
        labels, counts = [], []
        prev = 0
        for t in thresholds:
            n = int(((gnu > prev) & (gnu <= t)).sum())
            labels.append(f"={t}" if prev == 0 else f"{prev+1}-{t}")
            counts.append(n)
            prev = t
        n_above = int((gnu > thresholds[-1]).sum())
        labels.append(f">{thresholds[-1]//1000}K")
        counts.append(n_above)
    else:
        summ_path = tbls / "07_gnu_distribution_summary.tsv"
        if not summ_path.exists():
            print("  SKIP: no cache or summary", file=sys.stderr)
            return
        summ = pd.read_csv(summ_path, sep="\t")
        labels = [str(x) for x in summ["gnu_score"].values]
        vals = summ["n_alleles_at_most"].values
        counts = list(np.diff(np.concatenate([[0], vals])))

    fig, ax = plt.subplots(figsize=(6, 3.5))
    x = np.arange(len(labels))
    bars = ax.bar(x, counts, color="#3C5488", edgecolor="white", linewidth=0.3)
    for bar, c in zip(bars, counts):
        if c > 0:
            txt = f"{c:,.0f}" if c < 1e6 else f"{c/1e6:.1f}M"
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height(),
                    txt, ha="center", va="bottom", fontsize=5, color="#333333")
    ax.set_xticks(x)
    ax.set_xticklabels(labels, rotation=45, ha="right")
    ax.set_yscale("log")
    ax.set_xlabel("GNU score range")
    ax.set_ylabel("Number of alleles")
    ax.set_title("Distribution of allele frequency (GNU scores)")
    save(fig, figs / "pub_02_gnu_distribution.png", dpi)


# ======================================================================
# PLOT 3 -- Coverage stratified bar
# ======================================================================
def plot3_coverage_bars(tbls, figs, dpi):
    """Grouped bar: total genomes / 0.99 / 0.90 coverage per species.
    Produces both log and linear y-axis versions. Excludes Unknown."""
    print("[plot3] Coverage stratified bars", file=sys.stderr)
    cov_path = tbls / "03_species_coverage_estimates.tsv"
    if not cov_path.exists():
        print("  SKIP: coverage file not found", file=sys.stderr)
        return
    cov = pd.read_csv(cov_path, sep="\t")

    # Exclude Unknown/unclassified species
    skip_names = {"unknown", "unclassified", ""}
    cov = cov[~cov["species"].str.lower().str.strip().isin(skip_names)]

    species_order = (cov.groupby("species")["n_genomes_species"].first()
                     .sort_values(ascending=False).index.tolist())

    width = 0.25
    x = np.arange(len(species_order))

    totals, g90, g99 = [], [], []
    for sp in species_order:
        sub = cov[cov["species"] == sp]
        totals.append(sub["n_genomes_species"].iloc[0])
        r90 = sub[sub["target_fraction"] == 0.9]
        g90.append(r90["genomes_needed"].iloc[0] if len(r90) > 0 else 0)
        r99 = sub[sub["target_fraction"] == 0.99]
        g99.append(r99["genomes_needed"].iloc[0] if len(r99) > 0 else 0)

    labels = [abbrev(sp) for sp in species_order]

    for yscale, suffix in [("log", "log"), ("linear", "linear")]:
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.bar(x - width, totals, width, label="Total genomes",
               color="#3C5488", alpha=0.85)
        ax.bar(x, g99, width, label="99% allelic coverage",
               color="#E64B35", alpha=0.85)
        ax.bar(x + width, g90, width, label="90% allelic coverage",
               color="#00A087", alpha=0.85)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, rotation=60, ha="right", fontsize=6,
                           fontstyle="italic")
        if yscale == "log":
            ax.set_yscale("log")
        ax.set_ylabel("Number of genomes")
        ax.set_title("Genomes needed for allelic coverage")
        ax.legend(fontsize=7, loc="upper right")
        save(fig, figs / f"pub_03_coverage_bars_{suffix}.png", dpi)


# ======================================================================
# PLOT 4 -- Shared alleles heatmap
# ======================================================================
def plot4_heatmap(tbls, figs, dpi, top_n=30):
    """Heatmap of shared alleles between top N species (no Unknown)."""
    print(f"[plot4] Shared alleles heatmap (top {top_n})", file=sys.stderr)
    edges_path = tbls / "05_species_sharing_edges.tsv"
    nodes_path = tbls / "05_species_network_nodes.tsv"
    if not edges_path.exists():
        print("  SKIP: edges file not found", file=sys.stderr)
        return

    edges = pd.read_csv(edges_path, sep="\t")
    nodes = pd.read_csv(nodes_path, sep="\t")

    skip = {"Unknown", "unknown", "unclassified", "Unclassified", ""}
    nodes = nodes[~nodes["label"].isin(skip)]
    top_sp = nodes.sort_values("n_genomes", ascending=False).head(top_n)
    top_names = top_sp["label"].tolist()
    top_ids = set(top_sp["id"].tolist())

    e = edges[(edges["species_id_a"].isin(top_ids)) &
              (edges["species_id_b"].isin(top_ids))]

    name_idx = {n: i for i, n in enumerate(top_names)}
    M = np.zeros((top_n, top_n))
    for _, row in e.iterrows():
        a, b = row["species_a"], row["species_b"]
        if a in name_idx and b in name_idx:
            i, j = name_idx[a], name_idx[b]
            M[i, j] = M[j, i] = row["shared_alleles"]

    M_log = np.log10(M + 1)
    short = [abbrev(n) for n in top_names]

    # Version 1: log-transformed
    fig, ax = plt.subplots(figsize=(8, 7))
    im = ax.imshow(M_log, cmap="YlOrRd", aspect="equal")
    ax.set_xticks(range(len(short)))
    ax.set_yticks(range(len(short)))
    ax.set_xticklabels(short, rotation=90, fontsize=5, fontstyle="italic")
    ax.set_yticklabels(short, fontsize=5, fontstyle="italic")
    cbar = fig.colorbar(im, ax=ax, shrink=0.7, pad=0.02)
    cbar.set_label("log10(shared alleles + 1)", fontsize=7)
    ax.set_title(f"Shared alleles between top {top_n} species (log scale)")
    save(fig, figs / "pub_04_shared_heatmap_log.png", dpi)

    # Version 2: raw numbers
    fig2, ax2 = plt.subplots(figsize=(8, 7))
    im2 = ax2.imshow(M, cmap="YlOrRd", aspect="equal")
    ax2.set_xticks(range(len(short)))
    ax2.set_yticks(range(len(short)))
    ax2.set_xticklabels(short, rotation=90, fontsize=5, fontstyle="italic")
    ax2.set_yticklabels(short, fontsize=5, fontstyle="italic")
    cbar2 = fig2.colorbar(im2, ax=ax2, shrink=0.7, pad=0.02,
                           format=mticker.FuncFormatter(
                               lambda x, _: f"{x/1000:.0f}K" if x >= 1000
                               else f"{x:.0f}"))
    cbar2.set_label("Shared alleles", fontsize=7)
    ax2.set_title(f"Shared alleles between top {top_n} species (raw counts)")
    save(fig2, figs / "pub_04_shared_heatmap_raw.png", dpi)


# ======================================================================
# PLOT 5 -- Network
# ======================================================================
def plot5_network(tbls, figs, dpi, top_n=30, min_shared=100):
    """Force-directed species sharing network."""
    print("[plot5] Species sharing network", file=sys.stderr)
    try:
        import networkx as nx
    except ImportError:
        print("  SKIP: pip install networkx", file=sys.stderr)
        return

    edges_path = tbls / "05_species_sharing_edges.tsv"
    nodes_path = tbls / "05_species_network_nodes.tsv"
    if not edges_path.exists():
        print("  SKIP: edges file not found", file=sys.stderr)
        return

    edges = pd.read_csv(edges_path, sep="\t")
    nodes = pd.read_csv(nodes_path, sep="\t")

    skip = {"Unknown", "unknown", "unclassified", "Unclassified", ""}
    nodes = nodes[~nodes["label"].isin(skip)]
    top_sp = nodes.sort_values("n_genomes", ascending=False).head(top_n)
    top_ids = set(top_sp["id"].tolist())

    e = edges[(edges["species_id_a"].isin(top_ids)) &
              (edges["species_id_b"].isin(top_ids)) &
              (edges["shared_alleles"] >= min_shared)]

    G = nx.Graph()
    for _, row in top_sp.iterrows():
        sid = row["id"]
        name = row["label"]
        g = genus_of(name)
        G.add_node(sid, label=abbrev(name), genus=g,
                   n_genomes=row["n_genomes"])

    for _, row in e.iterrows():
        G.add_edge(row["species_id_a"], row["species_id_b"],
                   weight=row["shared_alleles"])

    if len(G.nodes) == 0:
        print("  SKIP: empty graph", file=sys.stderr)
        return

    # Use log-inverse weights for layout so high-sharing nodes
    # stay close but don't collapse into a single point
    layout_G = G.copy()
    for u, v, d in layout_G.edges(data=True):
        d["weight"] = 1.0 / (np.log10(d["weight"] + 1) + 0.1)
    try:
        pos = nx.kamada_kawai_layout(G, weight="weight")
    except Exception:
        pos = nx.spring_layout(G, k=5.0, iterations=200, seed=42,
                               weight=None)

    node_sizes = [max(np.log10(G.nodes[n].get("n_genomes", 100) + 1) * 120, 50)
                  for n in G.nodes]
    genera = list(set(G.nodes[n]["genus"] for n in G.nodes))
    gcol = {g: PALETTE[i % len(PALETTE)] for i, g in enumerate(genera)}
    ncols = [gcol[G.nodes[n]["genus"]] for n in G.nodes]

    edge_ws = [G[u][v]["weight"] for u, v in G.edges]
    max_w = max(edge_ws) if edge_ws else 1
    e_lw = [np.log10(w + 1) / np.log10(max_w + 1) * 4 + 0.2 for w in edge_ws]
    e_alpha = [min(0.1 + 0.6 * (w / max_w), 0.8) for w in edge_ws]

    fig, ax = plt.subplots(figsize=(10, 9))
    for (u, v), lw, al in zip(G.edges, e_lw, e_alpha):
        ax.plot([pos[u][0], pos[v][0]], [pos[u][1], pos[v][1]],
                color="#888888", linewidth=lw, alpha=al, zorder=1)
    nx.draw_networkx_nodes(G, pos, ax=ax, node_size=node_sizes,
                           node_color=ncols, edgecolors="white",
                           linewidths=0.5, alpha=0.85)
    # Manual labels with offset to avoid node overlap
    for n in G.nodes:
        x, y = pos[n]
        ax.text(x, y + 0.03, G.nodes[n]["label"], fontsize=5.5,
                ha="center", va="bottom", color="#333333")
    ax.set_title(f"Species allele sharing network (top {top_n}, "
                 f"edges >= {min_shared:,} shared)")
    ax.axis("off")

    seen = set()
    handles = []
    for n in G.nodes:
        g = G.nodes[n]["genus"]
        if g not in seen:
            seen.add(g)
            handles.append(Line2D([0], [0], marker="o", color="w",
                                  markerfacecolor=gcol[g], markersize=6, label=g))
    if handles:
        ax.legend(handles=handles, loc="lower left", fontsize=5,
                  ncol=2, framealpha=0.8, title="Genus", title_fontsize=6)
    save(fig, figs / "pub_05_network.png", dpi)


# ======================================================================
# PLOT 6 -- Protein count (proxy genome size) vs alleles vs genomes
# ======================================================================

def plot6_protein_vs_alleles(merged_faa, summary_df, species_stats,
                             selected_species, figs, dpi, top_n_color=30):
    """Two panels × two versions (median and mean protein count).

    Styling:
      - Top N species (by genome count from allele summary) get distinct colors + legend.
      - All other species are gray.
      - Labels are placed only for top species with simple repulsion.
    """
    print("[plot6] Protein count vs alleles (proxy for genome size)",
          file=sys.stderr)

    if merged_faa is None or merged_faa.empty:
        print("  SKIP: no per-genome protein data", file=sys.stderr)
        return
    if summary_df is None or summary_df.empty:
        print("  SKIP: no allele summary", file=sys.stderr)
        return

    # Compute per-species protein stats
    prot_stats = merged_faa.groupby("species")["n_proteins"].agg(
        ["median", "mean", "std", "count"]).reset_index()
    prot_stats.columns = ["species", "median_proteins", "mean_proteins",
                          "std_proteins", "n_genomes_faa"]

    # Determine allele + genome columns
    if "n_alleles_in_species" in summary_df.columns:
        allele_col = "n_alleles_in_species"
        genome_col = "n_genomes_in_species"
    else:
        allele_col = "n_alleles"
        genome_col = "n_genomes"

    # Top species list (from allele summary) for consistent coloring
    top_species, sp2col = _top_species_color_map(
        summary_df, species_col="species", rank_col=genome_col, top_n=top_n_color
    )

    # Merge with allele summary
    plot_df = prot_stats.merge(
        summary_df[["species", allele_col, genome_col]],
        on="species", how="inner")
    plot_df = plot_df.rename(columns={allele_col: "n_alleles",
                                      genome_col: "n_genomes"})

    if selected_species is not None:
        plot_df = plot_df[plot_df["species"].isin(selected_species)]

    if plot_df.empty:
        print("  SKIP: no overlapping species", file=sys.stderr)
        return

    is_top = plot_df["species"].isin(set(top_species)).values

    sizes = np.sqrt(plot_df["n_genomes"].values) * 0.35
    sizes = np.clip(sizes, 15, 250)

    for stat, label_stat in [("median_proteins", "Median"),
                             ("mean_proteins", "Mean")]:
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11, 5))

        # --- Panel A: protein count vs alleles
        if (~is_top).any():
            ax1.scatter(plot_df.loc[~is_top, stat],
                        plot_df.loc[~is_top, "n_alleles"],
                        s=sizes[~is_top], c="#BDBDBD", alpha=0.45,
                        edgecolors="white", linewidth=0.25, zorder=2)
        if is_top.any():
            top_df = plot_df.loc[is_top].copy()
            top_colors = [sp2col.get(s, "#333333") for s in top_df["species"]]
            ax1.scatter(top_df[stat], top_df["n_alleles"],
                        s=sizes[is_top], c=top_colors, alpha=0.80,
                        edgecolors="white", linewidth=0.35, zorder=3)

            #_annotate_spiral_no_overlap(
            #    ax1,
            #    top_df[stat].values,
            #    top_df["n_alleles"].values,
            #    [abbrev(s) for s in top_df["species"].values],
            #    fontsize=4.8, color="#555555")

        ax1.set_xlabel(f"{label_stat} proteins per genome")
        ax1.set_ylabel("Total unique alleles")
        ax1.set_yscale("log")
        ax1.set_title(f"(A) {label_stat} proteome size vs allelic diversity")

        # --- Panel B: n_genomes vs alleles
        if (~is_top).any():
            ax2.scatter(plot_df.loc[~is_top, "n_genomes"],
                        plot_df.loc[~is_top, "n_alleles"],
                        s=sizes[~is_top], c="#BDBDBD", alpha=0.45,
                        edgecolors="white", linewidth=0.25, zorder=2)
        if is_top.any():
            top_df = plot_df.loc[is_top].copy()
            top_colors = [sp2col.get(s, "#333333") for s in top_df["species"]]
            ax2.scatter(top_df["n_genomes"], top_df["n_alleles"],
                        s=sizes[is_top], c=top_colors, alpha=0.80,
                        edgecolors="white", linewidth=0.35, zorder=3)

            #_annotate_spiral_no_overlap(
            #    ax2,
            #    top_df["n_genomes"].values,
            #    top_df["n_alleles"].values,
            #    [abbrev(s) for s in top_df["species"].values],
            #    fontsize=4.8, color="#555555")

        ax2.set_xlabel("Number of genomes sequenced")
        ax2.set_ylabel("Total unique alleles")
        ax2.set_xscale("log")
        ax2.set_yscale("log")
        ax2.set_title("(B) Sampling depth vs allelic diversity")

        # Color legend (top species) — one per figure
        from matplotlib.lines import Line2D
        color_handles = [Line2D([0], [0], marker='o', linestyle='',
                                markerfacecolor=sp2col[sp], markeredgecolor="white",
                                markeredgewidth=0.4, markersize=5,
                                label=abbrev(sp))
                         for sp in top_species]
        color_handles.append(
            Line2D([0], [0], marker='o', linestyle='', markerfacecolor="#BDBDBD",
                   markeredgecolor="white", markeredgewidth=0.4,
                   markersize=5, label="Other species")
        )
        ax2.legend(handles=color_handles, title=f"Top {len(top_species)} species",
                   loc="center left", bbox_to_anchor=(1.02, 0.5),
                   framealpha=0.85, fontsize=6, title_fontsize=7,
                   ncol=1, borderaxespad=0.0, labelspacing=0.35)

        fig.suptitle(f"Allelic diversity: proteome size ({label_stat.lower()}) "
                     f"vs sequencing depth", fontsize=11, y=1.02)
        tag = label_stat.lower()
        save(fig, figs / f"pub_06_protein_vs_alleles_{tag}.png", dpi)


# ======================================================================
# PLOT 7 -- Rank-abundance + singleton inset
# ======================================================================
def plot7_allele_frequency(cache_npz, figs, dpi):
    """Two separate clear plots from GNU data:
    7A: Allele frequency class breakdown (how rare/common are alleles?)
    7B: Cumulative distribution (what fraction of alleles appear in ≤N genomes?)
    """
    print("[plot7] Allele frequency analysis", file=sys.stderr)
    if not cache_npz or not Path(cache_npz).exists():
        print("  SKIP: cache NPZ not found", file=sys.stderr)
        return
    z = np.load(cache_npz, allow_pickle=False)
    gnu = z["gnu"]
    N = len(gnu)

    # ── Plot 7A: Frequency class breakdown ────────────────────────────
    # Define biologically meaningful bins
    bins = [
        ("Singletons\n(GNU = 1)", (gnu == 1).sum()),
        ("Very rare\n(GNU 2-5)", ((gnu >= 2) & (gnu <= 5)).sum()),
        ("Rare\n(GNU 6-100)", ((gnu >= 6) & (gnu <= 100)).sum()),
        ("Moderate\n(GNU 101-1K)", ((gnu >= 101) & (gnu <= 1000)).sum()),
        ("Common\n(GNU 1K-10K)", ((gnu >= 1001) & (gnu <= 10000)).sum()),
        ("Widespread\n(GNU 10K-100K)", ((gnu >= 10001) & (gnu <= 100000)).sum()),
        ("Ubiquitous\n(GNU > 100K)", (gnu > 100000).sum()),
    ]
    labels_a = [b[0] for b in bins]
    counts_a = [int(b[1]) for b in bins]
    pcts_a = [c / N * 100 for c in counts_a]

    colors_a = ["#DC0000", "#E64B35", "#F39B7F", "#8491B4",
                "#4DBBD5", "#00A087", "#3C5488"]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    bars = ax.barh(range(len(labels_a)), counts_a, color=colors_a,
                   edgecolor="white", linewidth=0.5, height=0.7)

    # Annotate with count + percentage
    for i, (bar, c, p) in enumerate(zip(bars, counts_a, pcts_a)):
        if c > 0:
            if c >= 1e6:
                txt = f"{c/1e6:.1f}M ({p:.1f}%)"
            elif c >= 1e3:
                txt = f"{c/1e3:.0f}K ({p:.1f}%)"
            else:
                txt = f"{c:,} ({p:.1f}%)"
            ax.text(bar.get_width() + max(counts_a) * 0.01,
                    bar.get_y() + bar.get_height() / 2,
                    txt, va="center", fontsize=7, color="#333333")

    ax.set_yticks(range(len(labels_a)))
    ax.set_yticklabels(labels_a, fontsize=7)
    ax.set_xscale("log")
    ax.set_xlabel("Number of alleles")
    ax.set_title(f"Allele frequency classes across {N/1e6:.0f}M unique alleles")
    ax.invert_yaxis()
    save(fig, figs / "pub_07a_frequency_classes.png", dpi)

    # ── Plot 7B: Cumulative distribution ──────────────────────────────
    # What fraction of alleles appear in at most N genomes?
    thresholds = [1, 2, 3, 5, 10, 20, 50, 100, 500, 1000, 5000, 10000,
                  50000, 100000, 500000]
    cum_counts = [int((gnu <= t).sum()) for t in thresholds]
    cum_frac = [c / N * 100 for c in cum_counts]

    fig2, ax2 = plt.subplots(figsize=(6, 4))
    ax2.plot(thresholds, cum_frac, "o-", color="#3C5488", linewidth=1.5,
             markersize=4, markerfacecolor="#E64B35", markeredgecolor="white",
             markeredgewidth=0.5)
    ax2.set_xscale("log")
    ax2.set_xlabel("GNU score threshold (number of genomes)")
    ax2.set_ylabel("Cumulative % of alleles")
    ax2.set_title("Cumulative allele frequency distribution")
    ax2.set_ylim(0, 105)

    # Annotate key milestones
    for t, f in zip(thresholds, cum_frac):
        if t in (1, 5, 100, 1000, 10000):
            ax2.annotate(f"{f:.1f}%", xy=(t, f),
                         fontsize=6, color="#333333",
                         xytext=(0, 8), textcoords="offset points",
                         ha="center")

    # Horizontal reference lines
    for pct in [50, 90, 99]:
        ax2.axhline(pct, color="#cccccc", linewidth=0.5, linestyle="--")
        ax2.text(thresholds[0] * 0.8, pct + 1, f"{pct}%", fontsize=5,
                 color="#999999")

    save(fig2, figs / "pub_07b_cumulative_distribution.png", dpi)


# ======================================================================
# PLOT 8 -- Protein count distribution per species (violin/swarm)
# ======================================================================
def plot8_protein_distribution(merged_faa, selected_species, figs, dpi,
                               top_n=50):
    """Violin + box + strip plot of protein counts per species."""
    print("[plot8] Protein count distribution", file=sys.stderr)
    if merged_faa is None or merged_faa.empty:
        print("  SKIP: no protein count data", file=sys.stderr)
        return
    try:
        import seaborn as sns
    except ImportError:
        print("  SKIP: pip install seaborn", file=sys.stderr)
        return

    df = merged_faa.copy()
    if selected_species is not None:
        df = df[df["species"].isin(selected_species)]

    sp_stats = df.groupby("species")["n_proteins"].agg(["median", "count"])
    sp_stats = sp_stats[sp_stats["count"] >= 10]
    sp_stats = sp_stats.sort_values("median", ascending=True).tail(top_n)
    top_sp = sp_stats.index.tolist()

    df = df[df["species"].isin(top_sp)].copy()
    df["species"] = pd.Categorical(df["species"], categories=top_sp,
                                    ordered=True)

    label_map = {sp: f"{abbrev(sp)} (n={int(sp_stats.loc[sp, 'count']):,})"
                 for sp in top_sp}

    fig_h = max(6, len(top_sp) * 0.28)
    fig, ax = plt.subplots(figsize=(8, fig_h))

    # Use density_norm for newer seaborn, fall back to scale for older
    try:
        sns.violinplot(data=df, y="species", x="n_proteins", ax=ax,
                       orient="h", inner=None, color="#4DBBD5", alpha=0.3,
                       linewidth=0.3, density_norm="width", cut=0)
    except TypeError:
        sns.violinplot(data=df, y="species", x="n_proteins", ax=ax,
                       orient="h", inner=None, color="#4DBBD5", alpha=0.3,
                       linewidth=0.3, scale="width", cut=0)

    # Subsample for strip plot — sample per species without groupby.apply
    if len(df) > 200_000:
        strip_parts = []
        for sp in top_sp:
            sp_df = df[df["species"] == sp]
            if len(sp_df) > 2000:
                sp_df = sp_df.sample(2000, random_state=42)
            strip_parts.append(sp_df)
        strip_df = pd.concat(strip_parts, ignore_index=True)
        strip_df["species"] = pd.Categorical(strip_df["species"],
                                              categories=top_sp, ordered=True)
    else:
        strip_df = df

    sns.stripplot(data=strip_df, y="species", x="n_proteins", ax=ax,
                  orient="h", size=0.8, alpha=0.15, color="#3C5488",
                  jitter=True)
    sns.boxplot(data=df, y="species", x="n_proteins", ax=ax,
                orient="h", width=0.15, showcaps=True, showfliers=False,
                boxprops=dict(facecolor="white", edgecolor="black",
                              linewidth=0.5),
                whiskerprops=dict(linewidth=0.5),
                medianprops=dict(color="#E64B35", linewidth=1),
                capprops=dict(linewidth=0.5))

    ax.set_yticklabels([label_map.get(sp, sp) for sp in top_sp],
                       fontsize=5, fontstyle="italic")
    ax.set_xlabel("Number of proteins per genome")
    ax.set_ylabel("")
    ax.set_title("Protein count distribution per species")
    save(fig, figs / "pub_08_protein_distribution.png", dpi)


# ======================================================================
# MAIN
# ======================================================================
def main():
    ap = argparse.ArgumentParser(
        description="Publication-quality plots from ATB allelome results (v2)")

    # Allelome output directories
    ap.add_argument("--tables_dir", required=True, type=Path,
                    help="allelome_results/tables (from v5_v2)")
    ap.add_argument("--figures_dir", required=True, type=Path,
                    help="Output dir for publication figures")

    # ATB metadata files
    ap.add_argument("--samples_tsv", required=True, type=Path,
                    help="samples_with_ids.tsv: SampleID  Sample  SpeciesID  Species  HQ")
    ap.add_argument("--species_stats_tsv", required=True, type=Path,
                    help="species_stats.tsv: SpeciesID  Species  n_samples  n_HQ_T  n_HQ_F")
    ap.add_argument("--records_per_faa", type=Path, default=None,
                    help="TSV: sample_name  record_count (one row per genome)")
    ap.add_argument("--records_per_species", type=Path, default=None,
                    help="TSV: species_id  species_name  total_records (unused in plots, for reference)")
    ap.add_argument("--cache_npz", type=Path, default=None,
                    help="counts_cache.npz for GNU analysis (plots 2, 7)")

    # Control
    ap.add_argument("--top_n_species", type=int, default=80,
                    help="Number of top species (by n_genomes) for scatter/violin plots")
    ap.add_argument("--top_n_label", type=int, default=30,
                    help="How many species to label on plot 1")
    ap.add_argument("--top_n_color", type=int, default=30,
                    help="How many top species to color distinctly (plots 1 & 6); others are gray")
    ap.add_argument("--top_n_heatmap", type=int, default=30)
    ap.add_argument("--top_n_network", type=int, default=30)
    ap.add_argument("--top_n_violin", type=int, default=50,
                    help="Number of species for plot 8 violin")
    ap.add_argument("--min_shared_network", type=int, default=100)
    ap.add_argument("--dpi", type=int, default=300)

    args = ap.parse_args()
    tbls = args.tables_dir
    figs = args.figures_dir
    figs.mkdir(parents=True, exist_ok=True)

    # == Load species stats -> derive top N species list ================
    species_stats = load_species_stats(args.species_stats_tsv)
    selected_species = species_stats.head(args.top_n_species)["species"].tolist()
    print(f"[setup] top {args.top_n_species} species from "
          f"{len(species_stats)} total", file=sys.stderr)

    # == Load samples (for joining faa records to species) ==============
    samples = load_samples(args.samples_tsv)
    print(f"[setup] {len(samples):,} samples loaded", file=sys.stderr)

    # == Load & join records_per_faa ====================================
    merged_faa = None
    if args.records_per_faa and args.records_per_faa.exists():
        faa_df = load_records_per_faa(args.records_per_faa)
        merged_faa = join_faa_with_species(faa_df, samples)
        print(f"[setup] {len(merged_faa):,} genomes with protein counts "
              f"({merged_faa['species'].nunique()} species)", file=sys.stderr)
    else:
        print("[setup] no --records_per_faa; plots 6 & 8 skipped",
              file=sys.stderr)

    # == Load allele summary ============================================
    summary_path = tbls / "NEW5_all_species_summary.tsv"
    summary_df = None
    if summary_path.exists():
        summary_df = pd.read_csv(summary_path, sep="\t")
        print(f"[setup] allele summary: {len(summary_df)} species",
              file=sys.stderr)

    # == Generate plots =================================================
    if summary_df is not None:
        plot1_alleles_vs_genomes(summary_df, selected_species,
                                args.top_n_label, figs, args.dpi, top_n_color=args.top_n_color)
    else:
        print("[plot1] SKIP: NEW5_all_species_summary.tsv not found",
              file=sys.stderr)

    plot2_gnu_distribution(tbls, figs, args.dpi, args.cache_npz)
    plot3_coverage_bars(tbls, figs, args.dpi)
    plot4_heatmap(tbls, figs, args.dpi, top_n=args.top_n_heatmap)
    plot5_network(tbls, figs, args.dpi, top_n=args.top_n_network,
                  min_shared=args.min_shared_network)

    if merged_faa is not None and summary_df is not None:
        plot6_protein_vs_alleles(merged_faa, summary_df, species_stats,
                                selected_species, figs, args.dpi, top_n_color=args.top_n_color)
    else:
        print("[plot6] SKIP: need --records_per_faa + allele summary",
              file=sys.stderr)

    plot7_allele_frequency(args.cache_npz, figs, args.dpi)

    if merged_faa is not None:
        plot8_protein_distribution(merged_faa, selected_species, figs,
                                  args.dpi, top_n=args.top_n_violin)
    else:
        print("[plot8] SKIP: need --records_per_faa", file=sys.stderr)

    print(f"\n[DONE] all figures in {figs}", file=sys.stderr)


if __name__ == "__main__":
    main()
