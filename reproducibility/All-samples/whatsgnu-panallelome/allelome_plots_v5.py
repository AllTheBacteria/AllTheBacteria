#!/usr/bin/env python3
"""
allelome_plots_v5.py

ATB WhatsGNU allelome analysis + plotting for build_info.json v5.

Original 9 tasks + 6 new features:
  NEW-1. All cross-species alleles with per-species genome breakdown
  NEW-2. Top 50 + top 100 function plots excluding hypothetical proteins
  NEW-3. All alleles shared between species pairs with >500 shared alleles
  NEW-4. All alleles found in >2 species with species list + GNU + function
  NEW-5. All-species summary (not just top 20)
  NEW-6. Genome counts per species in edges TSV

Architecture:
  Phase 1 — Counts-based (from NPZ cache; no LMDB)
  Phase 2 — Single postings scan (tasks 2-species, 5, 6, 8 + NEW-1,3,4,5,6)
  Phase 3 — Coverage scan (tasks 3, 4; optional, one extra postings pass)
"""

from __future__ import annotations

import argparse
import gzip
import heapq
import json
import math
import struct
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import lmdb
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
VAL_COUNTS = struct.Struct("<II")   # func_id, gnu
U32 = struct.Struct("<I")
CHUNK = 2_000_000                   # for chunked cache building
_EMPTY_U32 = np.zeros(0, dtype=np.uint32)

# Patterns to identify hypothetical proteins (case-insensitive)
HYPOTHETICAL_PATTERNS = (
    "hypothetical protein",
    "hypothetical",
    "uncharacterized protein",
    "putative uncharacterized",
    "predicted protein",
    "unknown function",
    "duf",
)


# ---------------------------------------------------------------------------
# LMDB helpers
# ---------------------------------------------------------------------------
def open_lmdb_ro(path: Path) -> lmdb.Environment:
    return lmdb.open(str(path), readonly=True, lock=False,
                     readahead=True, max_readers=2048, max_dbs=32, subdir=True)


def shard_path(root: Path, sid: int) -> Path:
    return root / f"shard_{sid:02x}"


# ---------------------------------------------------------------------------
# Varint / postings decoding
# ---------------------------------------------------------------------------
def decode_postings(v: bytes) -> np.ndarray:
    """Decode postings value: n:uint32 + delta+varint genome_ids."""
    if len(v) < 4:
        return _EMPTY_U32
    n = U32.unpack_from(v, 0)[0]
    if n == 0:
        return _EMPTY_U32
    payload = v[4:]
    if len(payload) == n:
        deltas = np.frombuffer(payload, dtype=np.uint8).astype(np.uint32)
        np.cumsum(deltas, out=deltas)
        return deltas
    buf = v
    ids = np.empty(n, dtype=np.uint32)
    pos = 4
    prev = 0
    for idx in range(n):
        val = 0
        shift = 0
        while True:
            b = buf[pos]
            pos += 1
            val |= (b & 0x7F) << shift
            if b < 128:
                break
            shift += 7
        prev += val
        ids[idx] = prev
    return ids


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------
def ensure_dir(p: Path):
    p.mkdir(parents=True, exist_ok=True)


def save_fig(path: Path):
    plt.tight_layout()
    plt.savefig(path, dpi=200, bbox_inches="tight")
    plt.close()


def is_hypothetical(name) -> bool:
    """Check if a function name is hypothetical/uncharacterized."""
    if name is None or not isinstance(name, str):
        return True
    nl = name.lower().strip()
    if nl == "" or nl == "nan":
        return True
    for pat in HYPOTHETICAL_PATTERNS:
        if pat in nl:
            return True
    return False


def read_functions_tsv_gz(path: Path | None) -> dict[int, str]:
    """Load func_id → function_name mapping."""
    if path is None or not path.exists():
        return {}
    df = pd.read_csv(path, sep="\t", compression="gzip")
    cols = {c.lower(): c for c in df.columns}
    id_col = None
    for cand in ("function_id", "func_id", "functionid"):
        if cand in cols:
            id_col = cols[cand]
            break
    if id_col is None:
        raise ValueError(f"functions file missing func_id column: {list(df.columns)}")
    name_col = None
    for cand in ("function", "product", "annotation", "desc", "description"):
        if cand in cols:
            name_col = cols[cand]
            break
    if name_col is None:
        name_col = df.columns[1]
    return dict(zip(df[id_col].astype(int), df[name_col].astype(str)))


def load_samples(path: Path) -> pd.DataFrame:
    """Load samples_with_ids.tsv → DataFrame with genome_id, species_id, species."""
    df = pd.read_csv(path, sep="\t")
    cols = {c.lower(): c for c in df.columns}
    for need in ("sampleid", "speciesid"):
        if need not in cols:
            raise ValueError(f"Need column {need} (case-insensitive). Found: {list(df.columns)}")
    if "species" in cols:
        df = df.rename(columns={cols["species"]: "species"})
    elif "species_name" in cols:
        df = df.rename(columns={cols["species_name"]: "species"})
    else:
        df["species"] = df[cols["speciesid"]].astype(str)
    df = df.rename(columns={cols["sampleid"]: "genome_id",
                            cols["speciesid"]: "species_id"})
    df["genome_id"] = df["genome_id"].astype(np.uint32)
    df["species_id"] = df["species_id"].astype(np.uint32)
    return df[["genome_id", "species_id", "species"]]


# ---------------------------------------------------------------------------
# Cache loading / building
# ---------------------------------------------------------------------------
def load_or_build_cache(cache_npz: Path, out_dir: Path, nshards: int):
    """Return (hashes_u8, func_id, gnu, shard) arrays from cache or LMDB."""
    if cache_npz.exists():
        z = np.load(cache_npz, allow_pickle=False)
        print(f"[cache] loaded {cache_npz} — {len(z['gnu']):,} alleles",
              file=sys.stderr)
        return (z["hashes_u8"],
                z["func_id"].astype(np.uint32),
                z["gnu"].astype(np.uint32),
                z["shard"].astype(np.uint8))

    print(f"[cache] not found; building from LMDB counts → {cache_npz}",
          file=sys.stderr)
    ensure_dir(cache_npz.parent)
    counts_root = out_dir / "lmdb_counts"
    all_h, all_f, all_g, all_s = [], [], [], []
    h_buf = np.empty((CHUNK, 16), dtype=np.uint8)
    f_buf = np.empty(CHUNK, dtype=np.uint32)
    g_buf = np.empty(CHUNK, dtype=np.uint32)
    pos = 0
    total = 0
    t0 = time.time()

    for sid in range(nshards):
        env = open_lmdb_ro(shard_path(counts_root, sid))
        cdbi = env.open_db(b"counts")
        with env.begin(db=cdbi, write=False) as txn:
            cur = txn.cursor()
            for k, v in cur:
                if len(k) != 16 or len(v) < 8:
                    continue
                h_buf[pos] = np.frombuffer(k, dtype=np.uint8, count=16).copy()
                f_buf[pos], g_buf[pos] = VAL_COUNTS.unpack_from(v, 0)
                pos += 1
                total += 1
                if pos == CHUNK:
                    all_h.append(h_buf[:pos].copy())
                    all_f.append(f_buf[:pos].copy())
                    all_g.append(g_buf[:pos].copy())
                    all_s.append(np.full(pos, sid, dtype=np.uint8))
                    pos = 0
        if pos > 0:
            all_h.append(h_buf[:pos].copy())
            all_f.append(f_buf[:pos].copy())
            all_g.append(g_buf[:pos].copy())
            all_s.append(np.full(pos, sid, dtype=np.uint8))
            pos = 0
        env.close()
        print(f"[cache] shard {sid} done ({total:,} cumulative)", file=sys.stderr)

    hashes_u8 = np.concatenate(all_h) if all_h else np.zeros((0, 16), dtype=np.uint8)
    func_id = np.concatenate(all_f) if all_f else np.zeros(0, dtype=np.uint32)
    gnu = np.concatenate(all_g) if all_g else np.zeros(0, dtype=np.uint32)
    shard = np.concatenate(all_s) if all_s else np.zeros(0, dtype=np.uint8)

    np.savez_compressed(cache_npz, hashes_u8=hashes_u8, func_id=func_id,
                        gnu=gnu, shard=shard,
                        format_version=np.asarray([5], dtype=np.uint8))
    print(f"[cache] wrote {cache_npz} — {total:,} alleles in "
          f"{(time.time() - t0) / 60:.1f} min", file=sys.stderr)
    return hashes_u8, func_id, gnu, shard


# ===================================================================
# PHASE 1 — Counts-based analyses (tasks 1, 2-func, 7, 9)
#            + NEW-2: top50/100 excluding hypothetical
# ===================================================================
def phase1_counts(gnu_arr, func_id_arr, hashes_u8, shard_arr,
                  func_name, figs, tbls, args):
    N = len(gnu_arr)
    print(f"\n[phase1] {N:,} alleles loaded", file=sys.stderr)

    # ------ Task 1: Global GNU histogram (log-log) ------
    gnu_max = int(gnu_arr.max())
    bins = np.unique(np.logspace(0, np.log10(max(gnu_max, 2)),
                                 args.gnu_bins).astype(np.int64))
    bins = np.append(bins, gnu_max + 1)

    plt.figure(figsize=(8, 5))
    plt.hist(gnu_arr, bins=bins, edgecolor="none", alpha=0.85)
    plt.xscale("log")
    plt.yscale("log")
    plt.xlabel("GNU score (# genomes containing allele)")
    plt.ylabel("Number of alleles")
    plt.title("Global allele frequency distribution")
    save_fig(figs / "01_global_gnu_hist.png")
    counts_h, edges_h = np.histogram(gnu_arr, bins=bins)
    pd.DataFrame({"bin_left": edges_h[:-1], "bin_right": edges_h[1:],
                   "n_alleles": counts_h}).to_csv(
        tbls / "01_global_gnu_hist_data.tsv", sep="\t", index=False)
    print("[phase1] task 1 done — global GNU histogram", file=sys.stderr)

    # ------ Task 2 (functions): function allele counts ------
    func_counts = np.bincount(func_id_arr)
    nonzero = np.nonzero(func_counts)[0]
    fc_df = pd.DataFrame({
        "func_id": nonzero,
        "n_alleles": func_counts[nonzero],
        "function": [func_name.get(int(x), "") for x in nonzero],
    }).sort_values("n_alleles", ascending=False).reset_index(drop=True)
    fc_df.to_csv(tbls / "02_functions_allele_counts.tsv",
                 sep="\t", index=False)

    # --- NEW-2: Top 50 and Top 100 EXCLUDING hypothetical proteins ---
    fc_no_hyp = fc_df[~fc_df["function"].apply(is_hypothetical)].reset_index(drop=True)
    n_hyp_excluded = len(fc_df) - len(fc_no_hyp)
    print(f"[phase1] NEW-2: excluded {n_hyp_excluded:,} hypothetical/uncharacterized "
          f"function entries from top function plots", file=sys.stderr)

    for topn in (50, 100):
        topN = fc_no_hyp.head(topn)
        if topN.empty:
            continue
        labels = topN["function"].str[:55].values
        plt.figure(figsize=(14, 7) if topn == 100 else (12, 6))
        plt.bar(range(len(topN)), topN["n_alleles"].values, color="#4878CF")
        plt.xticks(range(len(topN)), labels, rotation=90,
                   fontsize=4 if topn == 100 else 5)
        plt.xlabel(f"Function (top {topn}, excl. hypothetical)")
        plt.ylabel("# distinct alleles")
        plt.title(f"Allelic diversity per function (top {topn}, excl. hypothetical)")
        save_fig(figs / f"02_functions_top{topn}_no_hyp.png")
        topN.to_csv(tbls / f"02_functions_top{topn}_no_hyp.tsv",
                    sep="\t", index=False)

    # Also keep the original top50 WITH hypothetical for reference
    top50_all = fc_df.head(50)
    labels_all = top50_all["function"].str[:60].values
    plt.figure(figsize=(12, 6))
    plt.bar(range(len(top50_all)), top50_all["n_alleles"].values, color="#8B8B8B")
    plt.xticks(range(len(top50_all)), labels_all, rotation=90, fontsize=5)
    plt.xlabel("Function (top 50, all)")
    plt.ylabel("# distinct alleles")
    plt.title("Allelic diversity per function (top 50, including hypothetical)")
    save_fig(figs / "02_functions_top50_all.png")
    print("[phase1] task 2-func done — function allele counts + NEW-2 plots",
          file=sys.stderr)

    # ------ Task 7: Top/bottom 100 alleles by GNU ------
    order = np.argsort(gnu_arr)
    high_idx = order[-100:][::-1]
    non_single_mask = gnu_arr[order] > 1
    non_single_order = order[non_single_mask]
    if len(non_single_order) >= 100:
        low_idx = non_single_order[:100]
        low_note = "rarest non-singleton alleles (GNU > 1)"
    else:
        low_idx = order[:100]
        low_note = "rarest alleles (including singletons)"

    def make_allele_table(idx):
        return pd.DataFrame({
            "rank": np.arange(1, len(idx) + 1),
            "hash16": [hashes_u8[i].tobytes().hex() for i in idx],
            "gnu": gnu_arr[idx].astype(int),
            "func_id": func_id_arr[idx].astype(int),
            "function": [func_name.get(int(x), "") for x in func_id_arr[idx]],
            "shard": shard_arr[idx].astype(int),
        })

    make_allele_table(high_idx).to_csv(
        tbls / "07_top100_alleles_by_gnu.tsv", sep="\t", index=False)
    make_allele_table(low_idx).to_csv(
        tbls / "07_bottom100_alleles_by_gnu.tsv", sep="\t", index=False)

    gnu_summary = pd.DataFrame({
        "gnu_score": [1, 2, 3, 4, 5, 10, 100, 1000, 10000],
        "n_alleles_at_most": [int((gnu_arr <= x).sum()) for x in
                              [1, 2, 3, 4, 5, 10, 100, 1000, 10000]],
    })
    gnu_summary.to_csv(tbls / "07_gnu_distribution_summary.tsv",
                       sep="\t", index=False)
    print(f"[phase1] task 7 done — top/bottom 100 ({low_note})", file=sys.stderr)

    # ------ Task 9: Dominance per function ------
    sort_idx = np.argsort(func_id_arr, kind="mergesort")
    fids_s = func_id_arr[sort_idx]
    gnus_s = gnu_arr[sort_idx]
    breaks = np.where(np.diff(fids_s.astype(np.int64)) != 0)[0] + 1
    starts = np.concatenate([[0], breaks])
    ends = np.concatenate([breaks, [len(fids_s)]])
    frac = args.dominance_fraction

    dom_rows = []
    for i in range(len(starts)):
        fid = int(fids_s[starts[i]])
        g = gnus_s[starts[i]:ends[i]]
        g_sorted = np.sort(g)[::-1]
        tot = g_sorted.astype(np.int64).sum()
        if tot == 0:
            k = 0
        else:
            cs = np.cumsum(g_sorted, dtype=np.int64)
            k = int(np.searchsorted(cs, frac * tot, side="left")) + 1
        dom_rows.append((fid, int(len(g)), int(tot), k))

    dom = pd.DataFrame(dom_rows,
                       columns=["func_id", "n_alleles", "gnu_total",
                                "n_alleles_to_reach_frac"])
    dom["fraction"] = frac
    dom["function"] = dom["func_id"].map(lambda x: func_name.get(int(x), ""))
    dom.sort_values(["n_alleles_to_reach_frac", "n_alleles"],
                    ascending=[True, False], inplace=True)
    dom.to_csv(tbls / "09_function_dominance.tsv", sep="\t", index=False)
    print("[phase1] task 9 done — function dominance", file=sys.stderr)


# ===================================================================
# PHASE 2 — Postings scan
#   Original: tasks 2-species, 5, 6, 8
#   NEW: 1 (cross-species alleles), 3 (>500 pairs), 4 (>2 species),
#        5 (all-species summary), 6 (genome counts in edges)
# ===================================================================
def phase2_postings(args, genome_to_species, species_id_to_name,
                    species_sizes, top_species_ids, n_genomes,
                    func_name, figs, tbls, unknown_sids):
    """Single scan of all postings shards."""
    postings_root = args.out_dir / "lmdb_postings"
    counts_root = args.out_dir / "lmdb_counts"
    nshards = args.nshards
    max_gid = len(genome_to_species) - 1

    top_set = set(int(x) for x in top_species_ids)
    top_sizes = {sid: int(species_sizes.get(sid, 1)) for sid in top_species_ids}

    # --- Pre-build fast lookup: is genome in a top species? ---
    max_sid = int(genome_to_species.max()) + 1
    is_top = np.zeros(max_sid + 1, dtype=bool)
    for sid in top_species_ids:
        is_top[sid] = True

    # --- Pre-build unknown filter mask ---
    is_unknown = np.zeros(max_sid + 1, dtype=bool)
    for uid in unknown_sids:
        is_unknown[uid] = True

    # --- Task 2 species: binned within-species GNU histograms ---
    species_hist = {}
    for sid in top_species_ids:
        species_hist[sid] = np.zeros(top_sizes[sid] + 2, dtype=np.int64)

    # --- NEW-5: all-species allele count (unique + shared already gives this) ---
    # We'll also count total alleles touching each species (including shared)
    alleles_per_species = np.zeros(max_sid + 1, dtype=np.int64)

    # --- Task 8: unique/shared per species ---
    unique_count = np.zeros(max_sid + 1, dtype=np.int64)
    shared_count = np.zeros(max_sid + 1, dtype=np.int64)

    # --- Task 5/6: species pair sharing matrix ---
    all_species_ids_sorted = np.array(sorted(species_sizes.index.astype(int).tolist()),
                                      dtype=np.int32)
    n_spp = len(all_species_ids_sorted)
    sid_to_midx = np.full(max_sid + 1, -1, dtype=np.int32)
    for i, sid in enumerate(all_species_ids_sorted):
        sid_to_midx[sid] = i

    pair_count = np.zeros((n_spp, n_spp), dtype=np.int64) if n_spp <= 15000 else None
    pair_rarity = np.zeros((n_spp, n_spp), dtype=np.float64) if n_spp <= 15000 else None
    if pair_count is None:
        pair_count_ctr = Counter()
        pair_rarity_ctr = Counter()
        print(f"[phase2] WARNING: {n_spp} species — using Counter for pairs",
              file=sys.stderr)

    # --- NEW-6: per-pair genome count sums ---
    # For each pair (i,j) where i<j in matrix indices, accumulate:
    #   pair_gsum_lo[i,j] = sum of genome counts from species i across shared alleles
    #   pair_gsum_hi[i,j] = sum of genome counts from species j across shared alleles
    # Then mean_genomes_a = pair_gsum_lo / pair_count gives average within-species
    # prevalence of shared alleles. This is much more informative than the union
    # of genome sets (which always converges to "all genomes" for large sharing).
    if n_spp <= 15000:
        pair_gsum_lo = np.zeros((n_spp, n_spp), dtype=np.int64)
        pair_gsum_hi = np.zeros((n_spp, n_spp), dtype=np.int64)
    else:
        pair_gsum_lo_ctr = Counter()
        pair_gsum_hi_ctr = Counter()

    # --- NEW-1,3,4: streaming output for cross-species alleles ---
    cross_species_path = tbls / "NEW1_cross_species_alleles.tsv.gz"
    cross_f = gzip.open(str(cross_species_path), "wt", compresslevel=3)
    cross_f.write("hash16\tfunc_id\tfunction\tgnu\tn_species\tspecies_composition\n")
    n_cross_written = 0

    processed = 0
    skipped_large = 0
    t0 = time.time()

    for shard_id in range(nshards):
        post_env = open_lmdb_ro(shard_path(postings_root, shard_id))
        cnt_env = open_lmdb_ro(shard_path(counts_root, shard_id))
        pdbi = post_env.open_db(b"postings")
        cdbi = cnt_env.open_db(b"counts")
        with post_env.begin(db=pdbi, write=False) as ptxn, \
             cnt_env.begin(db=cdbi, write=False) as ctxn:
            pcur = ptxn.cursor()
            for k, v in pcur:
                if len(k) != 16 or len(v) < 4:
                    continue
                gids = decode_postings(v)
                if gids.size == 0:
                    continue
                gids = gids[gids <= max_gid]
                if gids.size == 0:
                    continue

                sids = genome_to_species[gids]

                # --- Filter unknown if requested ---
                if not args.include_unknown and unknown_sids:
                    keep = ~is_unknown[sids]
                    if not keep.any():
                        processed += 1
                        continue
                    gids = gids[keep]
                    sids = sids[keep]

                uniq_sids = np.unique(sids)
                nspp = len(uniq_sids)

                # --- NEW-5: alleles per species (total, all species) ---
                for x in uniq_sids:
                    alleles_per_species[x] += 1

                # --- Task 8: unique vs shared ---
                if nspp == 1:
                    unique_count[uniq_sids[0]] += 1
                elif nspp > 1:
                    for x in uniq_sids:
                        shared_count[x] += 1

                # --- Task 2 species: within-species GNU ---
                top_mask = is_top[sids]
                if top_mask.any():
                    s_top = sids[top_mask]
                    u_top, c_top = np.unique(s_top, return_counts=True)
                    for ssid, cnt in zip(u_top, c_top):
                        ssid = int(ssid)
                        cnt = int(cnt)
                        if ssid in species_hist:
                            if cnt < len(species_hist[ssid]):
                                species_hist[ssid][cnt] += 1

                # --- NEW-1: cross-species allele streaming ---
                if nspp >= 2:
                    # Fetch func_id + GNU from counts
                    cv = ctxn.get(k)
                    if cv and len(cv) >= 8:
                        fid, gnu_g = VAL_COUNTS.unpack_from(cv, 0)
                    else:
                        fid = 0
                        gnu_g = int(gids.size)
                    fname = func_name.get(int(fid), "")
                    hash_hex = k.hex() if isinstance(k, bytes) else bytes(k).hex()

                    # Per-species genome counts for this allele
                    u_all, c_all = np.unique(sids, return_counts=True)
                    comp_parts = []
                    for sp_id, sp_cnt in zip(u_all, c_all):
                        sp_name = species_id_to_name.get(int(sp_id), str(sp_id))
                        comp_parts.append(f"{sp_name}:{int(sp_cnt)}")
                    composition = ";".join(comp_parts)

                    cross_f.write(f"{hash_hex}\t{fid}\t{fname}\t{gnu_g}\t"
                                  f"{nspp}\t{composition}\n")
                    n_cross_written += 1

                    w_rarity = 1.0 / max(float(gnu_g), 1.0)

                    # --- Task 5/6: species pair network ---
                    if nspp <= args.max_pairs_species:
                        midxs = sid_to_midx[uniq_sids]
                        midxs = midxs[midxs >= 0]
                        midxs.sort()

                        # Build midx → genome count for this allele
                        # (u_all, c_all already computed above for composition)
                        sid_to_cnt = {}
                        for sp_id, sp_cnt in zip(u_all, c_all):
                            mi = sid_to_midx[int(sp_id)]
                            if mi >= 0:
                                sid_to_cnt[mi] = int(sp_cnt)

                        if pair_count is not None:
                            for i in range(len(midxs)):
                                for j in range(i + 1, len(midxs)):
                                    mi, mj = midxs[i], midxs[j]
                                    pair_count[mi, mj] += 1
                                    pair_rarity[mi, mj] += w_rarity
                                    pair_gsum_lo[mi, mj] += sid_to_cnt.get(mi, 0)
                                    pair_gsum_hi[mi, mj] += sid_to_cnt.get(mj, 0)
                        else:
                            for i in range(len(midxs)):
                                for j in range(i + 1, len(midxs)):
                                    mi, mj = midxs[i], midxs[j]
                                    pair_count_ctr[(mi, mj)] += 1
                                    pair_rarity_ctr[(mi, mj)] += w_rarity
                                    pair_gsum_lo_ctr[(mi, mj)] += sid_to_cnt.get(mi, 0)
                                    pair_gsum_hi_ctr[(mi, mj)] += sid_to_cnt.get(mj, 0)
                    else:
                        skipped_large += 1

                processed += 1
                if args.progress_every and processed % args.progress_every == 0:
                    dt = time.time() - t0
                    print(f"[phase2] {processed:,} alleles | "
                          f"cross={n_cross_written:,} | "
                          f"skip_large={skipped_large:,} | "
                          f"{dt / 3600:.1f}h", file=sys.stderr)

        post_env.close()
        cnt_env.close()
        print(f"[phase2] shard {shard_id} done ({processed:,} cumulative)",
              file=sys.stderr)

    cross_f.close()
    dt_total = time.time() - t0
    print(f"[phase2] postings scan complete — {processed:,} alleles, "
          f"{n_cross_written:,} cross-species in {dt_total / 3600:.1f}h",
          file=sys.stderr)

    # ==================================================================
    # Write results
    # ==================================================================

    # --- Task 2 species: within-species GNU histograms ---
    hist_summary = []
    for sid in top_species_ids:
        h = species_hist[sid]
        nonzero_bins = np.nonzero(h)[0]
        if len(nonzero_bins) == 0:
            continue
        spname = species_id_to_name.get(int(sid), str(sid))
        total_alleles = int(h.sum())
        hist_summary.append({
            "species_id": int(sid), "species": spname,
            "n_alleles_in_species": total_alleles,
            "n_genomes_in_species": top_sizes.get(sid, 0),
        })
        hdf = pd.DataFrame({"within_species_gnu": nonzero_bins,
                             "n_alleles": h[nonzero_bins].astype(int)})
        hdf.to_csv(tbls / f"02_species_{int(sid)}_gnu_hist_data.tsv",
                   sep="\t", index=False)
        plt.figure(figsize=(7, 4))
        plt.bar(nonzero_bins, h[nonzero_bins], width=np.maximum(nonzero_bins * 0.02, 1),
                color="#4878CF", edgecolor="none", alpha=0.8)
        plt.xscale("log")
        plt.yscale("log")
        plt.xlabel("Within-species prevalence (# genomes in species)")
        plt.ylabel("Number of alleles")
        plt.title(f"{spname} — allele prevalence distribution")
        save_fig(figs / f"02_species_{int(sid)}_gnu_hist.png")

    pd.DataFrame(hist_summary).to_csv(
        tbls / "02_species_gnu_hists_top.tsv", sep="\t", index=False)
    print("[phase2] task 2-species done — within-species histograms",
          file=sys.stderr)

    # --- NEW-5: All-species summary ---
    all_sids = all_species_ids_sorted
    all_species_rows = []
    for sid in all_sids:
        all_species_rows.append({
            "species_id": int(sid),
            "species": species_id_to_name.get(int(sid), str(sid)),
            "n_genomes_in_species": int(species_sizes.get(int(sid), 0)),
            "n_alleles_in_species": int(alleles_per_species[sid]),
            "unique_alleles": int(unique_count[sid]),
            "shared_alleles": int(shared_count[sid]),
        })
    all_spp_df = pd.DataFrame(all_species_rows).sort_values(
        "n_genomes_in_species", ascending=False)
    all_spp_df.to_csv(tbls / "NEW5_all_species_summary.tsv",
                      sep="\t", index=False)
    print(f"[phase2] NEW-5 done — all-species summary ({len(all_spp_df):,} species)",
          file=sys.stderr)

    # --- Task 8: unique vs shared ---
    us_df = all_spp_df[["species_id", "species", "n_genomes_in_species",
                         "unique_alleles", "shared_alleles"]].copy()
    us_df = us_df.rename(columns={"n_genomes_in_species": "n_genomes"})
    us_df.to_csv(tbls / "08_unique_vs_shared_all_species.tsv",
                 sep="\t", index=False)
    us_top = us_df.head(args.top_species)
    us_top.to_csv(tbls / "08_unique_vs_shared_top_species.tsv",
                  sep="\t", index=False)

    plt.figure(figsize=(10, 6))
    x = np.arange(len(us_top))
    plt.bar(x - 0.2, us_top["unique_alleles"].values, width=0.4,
            label="Species-unique", color="#4878CF")
    plt.bar(x + 0.2, us_top["shared_alleles"].values, width=0.4,
            label="Shared with other species", color="#D65F5F")
    plt.xticks(x, us_top["species"].str[:30].values, rotation=90, fontsize=7)
    plt.xlabel("Species (top 20 by # genomes)")
    plt.ylabel("# alleles")
    plt.legend()
    plt.title("Species-unique vs shared alleles")
    save_fig(figs / "08_unique_vs_shared_top_species.png")
    print("[phase2] task 8 done — unique vs shared", file=sys.stderr)

    # --- Tasks 5 & 6 + NEW-6: species network edges with genome counts ---
    # NEW-6 columns:
    #   species_a_genome_hits = total genome-allele occurrences from A across shared alleles
    #   species_b_genome_hits = same for B
    #   species_a_mean_genomes = avg genomes from A per shared allele (hits / shared_alleles)
    #   species_b_mean_genomes = avg genomes from B per shared allele
    edges = []
    if pair_count is not None:
        ii, jj = np.nonzero(np.triu(pair_count, k=1))
        for idx in range(len(ii)):
            i, j = int(ii[idx]), int(jj[idx])
            sid_a = int(all_species_ids_sorted[i])
            sid_b = int(all_species_ids_sorted[j])
            n_shared = int(pair_count[i, j])
            gsum_a = int(pair_gsum_lo[i, j])
            gsum_b = int(pair_gsum_hi[i, j])
            edges.append({
                "species_id_a": sid_a,
                "species_a": species_id_to_name.get(sid_a, str(sid_a)),
                "species_id_b": sid_b,
                "species_b": species_id_to_name.get(sid_b, str(sid_b)),
                "shared_alleles": n_shared,
                "rarity_weight": float(pair_rarity[i, j]),
                "species_a_genome_hits": gsum_a,
                "species_b_genome_hits": gsum_b,
                "species_a_mean_genomes": round(gsum_a / max(n_shared, 1), 2),
                "species_b_mean_genomes": round(gsum_b / max(n_shared, 1), 2),
                "species_a_genomes_total": int(species_sizes.get(sid_a, 0)),
                "species_b_genomes_total": int(species_sizes.get(sid_b, 0)),
            })
    else:
        for (mi, mj), w in pair_count_ctr.items():
            sid_a = int(all_species_ids_sorted[mi])
            sid_b = int(all_species_ids_sorted[mj])
            n_shared = int(w)
            gsum_a = int(pair_gsum_lo_ctr.get((mi, mj), 0))
            gsum_b = int(pair_gsum_hi_ctr.get((mi, mj), 0))
            edges.append({
                "species_id_a": sid_a,
                "species_a": species_id_to_name.get(sid_a, str(sid_a)),
                "species_id_b": sid_b,
                "species_b": species_id_to_name.get(sid_b, str(sid_b)),
                "shared_alleles": n_shared,
                "rarity_weight": float(pair_rarity_ctr.get((mi, mj), 0.0)),
                "species_a_genome_hits": gsum_a,
                "species_b_genome_hits": gsum_b,
                "species_a_mean_genomes": round(gsum_a / max(n_shared, 1), 2),
                "species_b_mean_genomes": round(gsum_b / max(n_shared, 1), 2),
                "species_a_genomes_total": int(species_sizes.get(sid_a, 0)),
                "species_b_genomes_total": int(species_sizes.get(sid_b, 0)),
            })

    edges_df = pd.DataFrame(edges).sort_values("shared_alleles", ascending=False)
    edges_df.to_csv(tbls / "05_species_sharing_edges.tsv",
                    sep="\t", index=False)

    # Network nodes
    nodes_df = pd.DataFrame([
        {"id": int(sid),
         "label": species_id_to_name.get(int(sid), str(sid)),
         "n_genomes": int(species_sizes.get(int(sid), 0)),
         "n_alleles": int(alleles_per_species[sid]),
         "unique_alleles": int(unique_count[sid]),
         "shared_alleles": int(shared_count[sid])}
        for sid in all_sids
    ])
    nodes_df.to_csv(tbls / "05_species_network_nodes.tsv",
                    sep="\t", index=False)

    # Task 6: top 10 pairs
    top10 = edges_df.head(10)
    top10.to_csv(tbls / "06_top10_species_pairs.tsv",
                 sep="\t", index=False)
    print("[phase2] tasks 5 & 6 + NEW-6 done — species network with genome counts",
          file=sys.stderr)

    # Heatmap
    top_midxs = [int(sid_to_midx[sid]) for sid in top_species_ids
                 if sid_to_midx[sid] >= 0]
    top_names = [species_id_to_name.get(int(sid), str(sid))[:25]
                 for sid in top_species_ids
                 if sid_to_midx[sid] >= 0]

    if pair_count is not None and len(top_midxs) > 1:
        M = np.zeros((len(top_midxs), len(top_midxs)), dtype=np.float64)
        for ri, mi in enumerate(top_midxs):
            for ci, mj in enumerate(top_midxs):
                if mi < mj:
                    M[ri, ci] = pair_count[mi, mj]
                elif mj < mi:
                    M[ri, ci] = pair_count[mj, mi]
        M = M + M.T
        M_log = np.log10(M + 1)
        plt.figure(figsize=(9, 8))
        plt.imshow(M_log, cmap="YlOrRd")
        plt.xticks(range(len(top_names)), top_names, rotation=90, fontsize=6)
        plt.yticks(range(len(top_names)), top_names, fontsize=6)
        plt.colorbar(label="log10(shared alleles + 1)")
        plt.title("Shared alleles between top species")
        save_fig(figs / "05_species_sharing_heatmap.png")

    # ==================================================================
    # POST-PROCESSING: NEW-3 and NEW-4
    # Read the streaming cross-species file and filter
    # ==================================================================
    print("[phase2] post-processing cross-species alleles for NEW-3, NEW-4...",
          file=sys.stderr)

    # --- Identify species pairs with >500 shared alleles ---
    high_sharing_pairs = set()
    min_shared = args.min_shared_for_pair_report
    for _, row in edges_df.iterrows():
        if row["shared_alleles"] >= min_shared:
            # Store as frozenset of species names for matching
            high_sharing_pairs.add(
                frozenset([row["species_a"], row["species_b"]]))
    print(f"[phase2] {len(high_sharing_pairs)} species pairs with "
          f">={min_shared} shared alleles", file=sys.stderr)

    # --- Read back and filter ---
    new3_path = tbls / f"NEW3_alleles_pairs_gt{min_shared}_shared.tsv.gz"
    new4_path = tbls / "NEW4_alleles_in_gt2_species.tsv.gz"

    n_new3 = 0
    n_new4 = 0

    with gzip.open(str(cross_species_path), "rt") as fin, \
         gzip.open(str(new3_path), "wt", compresslevel=3) as f3, \
         gzip.open(str(new4_path), "wt", compresslevel=3) as f4:

        header = fin.readline().strip()
        f3.write(header + "\n")
        f4.write(header + "\n")

        for line in fin:
            parts = line.strip().split("\t")
            if len(parts) < 6:
                continue
            n_species = int(parts[4])
            composition = parts[5]

            # NEW-4: alleles in >2 species
            if n_species > 2:
                f4.write(line)
                n_new4 += 1

            # NEW-3: alleles belonging to high-sharing pairs
            if high_sharing_pairs and n_species >= 2:
                # Parse species names from composition
                sp_names = []
                for part in composition.split(";"):
                    colon_idx = part.rfind(":")
                    if colon_idx > 0:
                        sp_names.append(part[:colon_idx])
                # Check if any pair of species in this allele is a high-sharing pair
                write_new3 = False
                for i in range(len(sp_names)):
                    for j in range(i + 1, len(sp_names)):
                        if frozenset([sp_names[i], sp_names[j]]) in high_sharing_pairs:
                            write_new3 = True
                            break
                    if write_new3:
                        break
                if write_new3:
                    f3.write(line)
                    n_new3 += 1

    print(f"[phase2] NEW-3 done — {n_new3:,} alleles in pairs >={min_shared}",
          file=sys.stderr)
    print(f"[phase2] NEW-4 done — {n_new4:,} alleles in >2 species",
          file=sys.stderr)
    print(f"[phase2] NEW-1 done — {n_cross_written:,} total cross-species alleles "
          f"in {cross_species_path.name}", file=sys.stderr)

    return processed


# ===================================================================
# PHASE 3 — Coverage (tasks 3 & 4) — unchanged from user's working version
# ===================================================================
def phase3_coverage(args, genome_to_species, species_id_to_name,
                    species_sizes, top_species_ids, figs, tbls):
    """Per-species coverage estimation via greedy set cover."""
    postings_root = args.out_dir / "lmdb_postings"
    nshards = args.nshards
    max_gid = len(genome_to_species) - 1
    target_fracs = sorted(args.coverage_fractions)

    species_genome_ids = {}
    for sid in top_species_ids:
        mask = genome_to_species == sid
        gids = np.where(mask)[0].astype(np.uint32)
        species_genome_ids[sid] = set(gids.tolist())

    species_allele_postings: dict[int, list[np.ndarray]] = {
        sid: [] for sid in top_species_ids}

    max_sid = int(genome_to_species.max()) + 1
    is_target = np.zeros(max_sid + 1, dtype=bool)
    for sid in top_species_ids:
        is_target[sid] = True

    print(f"\n[phase3] coverage scan — collecting allele→genomes for "
          f"{len(top_species_ids)} species", file=sys.stderr)
    t0 = time.time()
    processed = 0

    for shard_id in range(nshards):
        post_env2 = open_lmdb_ro(shard_path(postings_root, shard_id))
        pdbi2 = post_env2.open_db(b"postings")
        with post_env2.begin(db=pdbi2, write=False) as ptxn2:
            pcur2 = ptxn2.cursor()
            for k, v in pcur2:
                if len(k) != 16 or len(v) < 4:
                    continue
                gids = decode_postings(v)
                if gids.size == 0:
                    continue
                gids = gids[gids <= max_gid]
                if gids.size == 0:
                    continue
                sids = genome_to_species[gids]

                if not is_target[sids].any():
                    processed += 1
                    continue

                for target_sid in top_species_ids:
                    mask = sids == target_sid
                    if mask.any():
                        species_allele_postings[target_sid].append(
                            gids[mask].copy())

                processed += 1
                if args.progress_every and processed % args.progress_every == 0:
                    dt = time.time() - t0
                    print(f"[phase3] {processed:,} alleles scanned | "
                          f"{dt / 3600:.1f}h", file=sys.stderr)
        post_env2.close()
        print(f"[phase3] shard {shard_id} done", file=sys.stderr)

    print(f"[phase3] scan done in {(time.time() - t0) / 3600:.1f}h — "
          f"running greedy per species", file=sys.stderr)

    all_coverage_rows = []
    all_selected_rows = []

    for sid in top_species_ids:
        spname = species_id_to_name.get(int(sid), str(sid))
        allele_posts = species_allele_postings[sid]
        n_alleles = len(allele_posts)
        n_genomes_sp = int(species_sizes.get(int(sid), 0))

        if n_alleles == 0:
            print(f"[phase3] {spname}: no alleles found, skipping", file=sys.stderr)
            continue

        print(f"[phase3] {spname}: {n_alleles:,} alleles, "
              f"{n_genomes_sp:,} genomes — building reverse index",
              file=sys.stderr)

        genome_allele_lists = defaultdict(list)
        for aidx, gids_sp in enumerate(allele_posts):
            for gid in gids_sp:
                genome_allele_lists[int(gid)].append(aidx)
        genome_allele_sets = {gid: set(als) for gid, als in genome_allele_lists.items()}
        del genome_allele_lists

        covered = set()
        heap = [(-len(als), gid) for gid, als in genome_allele_sets.items()]
        heapq.heapify(heap)

        selected = []
        reached = {}          # tf -> (iteration, n_covered, fraction)
        max_target = max(target_fracs)
        iteration = 0
        t_greedy = time.time()

        while heap and len(covered) < int(math.ceil(max_target * n_alleles)):
            neg_old, gid = heapq.heappop(heap)
            if gid not in genome_allele_sets:
                continue
            actual = genome_allele_sets[gid] - covered
            gain = len(actual)
            if gain == 0:
                del genome_allele_sets[gid]
                continue
            if heap and gain < -heap[0][0]:
                heapq.heappush(heap, (-gain, gid))
                continue
            covered |= actual
            iteration += 1
            n_covered = len(covered)
            frac_now = n_covered / n_alleles
            selected.append((gid, n_covered, frac_now))
            del genome_allele_sets[gid]

            for tf in target_fracs:
                if tf not in reached and frac_now >= tf:
                    reached[tf] = (iteration, n_covered, frac_now)

            if iteration % 5000 == 0:
                print(f"  [{spname}] iter {iteration}: "
                      f"covered={len(covered):,}/{n_alleles:,} "
                      f"({frac_now:.4%})", file=sys.stderr)

        greedy_time = time.time() - t_greedy
        print(f"[phase3] {spname}: greedy done in {greedy_time:.0f}s — "
              f"{len(selected)} genomes selected, "
              f"covered {len(covered):,}/{n_alleles:,} "
              f"({len(covered) / max(n_alleles, 1):.4%})", file=sys.stderr)

        for tf in target_fracs:
            if tf in reached:
                tf_iter, tf_covered, tf_frac = reached[tf]
            else:
                # threshold was never reached
                tf_iter = -1
                tf_covered = len(covered)
                tf_frac = len(covered) / max(n_alleles, 1)
            all_coverage_rows.append({
                "species_id": int(sid),
                "species": spname,
                "n_genomes_species": n_genomes_sp,
                "n_alleles_species": n_alleles,
                "target_fraction": tf,
                "genomes_needed": tf_iter,
                "alleles_covered": tf_covered,
                "achieved_fraction": tf_frac,
            })

        for iter_num, (gid, cum_cov, frac_now) in enumerate(selected, 1):
            all_selected_rows.append({
                "species_id": int(sid), "species": spname,
                "iteration": iter_num,
                "genome_id": int(gid),
                "cumulative_covered": cum_cov,
                "fraction_covered": frac_now,
            })

        species_allele_postings[sid] = []

    cov_df = pd.DataFrame(all_coverage_rows)
    cov_df.to_csv(tbls / "03_species_coverage_estimates.tsv",
                  sep="\t", index=False)

    if all_selected_rows:
        sel_df = pd.DataFrame(all_selected_rows)
        sel_df.to_csv(tbls / "03_species_coverage_selected_genomes.tsv",
                      sep="\t", index=False)

        total_unique_genomes = sel_df["genome_id"].nunique()
        task4_note = (f"Union of per-species greedy selections: "
                      f"{total_unique_genomes:,} distinct genomes across "
                      f"{len(top_species_ids)} species. "
                      f"This is an approximation of global coverage.")
        (tbls / "04_global_coverage_note.txt").write_text(task4_note)
        print(f"[phase3] task 4 note: {task4_note}", file=sys.stderr)

    if all_selected_rows:
        sel_df = pd.DataFrame(all_selected_rows)
        for sid in top_species_ids:
            sub = sel_df[sel_df["species_id"] == int(sid)]
            if sub.empty:
                continue
            spname = species_id_to_name.get(int(sid), str(sid))
            plt.figure(figsize=(7, 4))
            plt.plot(sub["iteration"].values, sub["fraction_covered"].values,
                     linewidth=1.2, color="#4878CF")
            for tf in target_fracs:
                plt.axhline(tf, color="gray", linestyle="--", linewidth=0.5)
            plt.xlabel("# genomes selected")
            plt.ylabel("Fraction of alleles covered")
            plt.title(f"{spname} — coverage curve")
            plt.ylim(0, 1.02)
            save_fig(figs / f"03_coverage_{int(sid)}.png")

    print("[phase3] tasks 3 & 4 done — coverage estimation", file=sys.stderr)


# ===================================================================
# MAIN
# ===================================================================
def main():
    ap = argparse.ArgumentParser(
        description="ATB allelome analysis — all tasks + new features (v5 revamped v2)")

    # Required
    ap.add_argument("--out_dir", required=True, type=Path,
                    help="WGNU_ATB3 root dir")
    ap.add_argument("--samples_with_ids_tsv", required=True, type=Path)
    ap.add_argument("--plots_out", required=True, type=Path,
                    help="Output dir for figures, tables, metadata")
    ap.add_argument("--nshards", type=int, required=True)

    # Optional inputs
    ap.add_argument("--functions_tsv_gz", type=Path, default=None)
    ap.add_argument("--species_stats_tsv", type=Path, default=None)
    ap.add_argument("--counts_cache_npz", type=Path, default=None)

    # Behavior
    ap.add_argument("--include_unknown", action="store_true",
                    help="Include species named Unknown/unclassified.")
    ap.add_argument("--dominance_fraction", type=float, default=0.90)
    ap.add_argument("--gnu_bins", type=int, default=300)
    ap.add_argument("--top_species", type=int, default=20)
    ap.add_argument("--max_pairs_species", type=int, default=200)
    ap.add_argument("--progress_every", type=int, default=2_000_000)
    ap.add_argument("--min_shared_for_pair_report", type=int, default=500,
                    help="NEW-3: minimum shared alleles for a pair to get "
                         "full allele listing (default: 500).")

    # Phase control
    ap.add_argument("--skip_postings", action="store_true")
    ap.add_argument("--do_coverage", action="store_true")
    ap.add_argument("--coverage_fractions", type=str, default="0.90,0.99")
    ap.add_argument("--coverage_top_n", type=int, default=None)

    args = ap.parse_args()
    args.coverage_fractions = [float(x) for x in args.coverage_fractions.split(",")]
    if args.coverage_top_n is None:
        args.coverage_top_n = args.top_species

    t_global = time.time()

    figs = args.plots_out / "figures"
    tbls = args.plots_out / "tables"
    ensure_dir(figs)
    ensure_dir(tbls)

    # --- Load functions ---
    if args.functions_tsv_gz is None:
        cand = args.out_dir / "metadata" / "functions.tsv.gz"
        args.functions_tsv_gz = cand if cand.exists() else None
    func_name = read_functions_tsv_gz(args.functions_tsv_gz)
    print(f"[setup] {len(func_name):,} functions loaded", file=sys.stderr)

    # --- Load samples/species ---
    samp = load_samples(args.samples_with_ids_tsv)
    n_genomes = int(samp["genome_id"].max()) + 1
    species_id_to_name = (samp.drop_duplicates("species_id")
                          .set_index("species_id")["species"].to_dict())
    species_sizes = (samp.groupby("species_id")["genome_id"]
                     .nunique().sort_values(ascending=False))

    unknown_sids = set()
    for sid, name in species_id_to_name.items():
        if name.lower().strip() in ("unknown", "unclassified", ""):
            unknown_sids.add(int(sid))
    if unknown_sids:
        print(f"[setup] identified {len(unknown_sids)} unknown/unclassified "
              f"species IDs: {sorted(unknown_sids)[:10]}...", file=sys.stderr)

    top_species_ids = None
    if args.species_stats_tsv and args.species_stats_tsv.exists():
        ss = pd.read_csv(args.species_stats_tsv, sep="\t")
        cols = {c.lower(): c for c in ss.columns}
        sid_col = cols.get("species_id") or cols.get("speciesid")
        ncol = (cols.get("n_genomes") or cols.get("genomes") or
                cols.get("count") or cols.get("n"))
        if sid_col and ncol:
            ss = ss.sort_values(ncol, ascending=False)
            top_species_ids = ss[sid_col].astype(int).head(args.top_species).tolist()
    if top_species_ids is None:
        top_species_ids = (species_sizes.head(args.top_species)
                           .index.astype(int).tolist())

    print(f"[setup] {n_genomes:,} genomes, "
          f"{len(species_sizes)} species, "
          f"top {len(top_species_ids)} selected", file=sys.stderr)

    gs_path = args.out_dir / "indexes" / "genome_species.u32"
    genome_to_species = np.fromfile(gs_path, dtype=np.uint32)
    if len(genome_to_species) < n_genomes:
        raise ValueError(f"genome_species.u32 length {len(genome_to_species)} "
                         f"< n_genomes {n_genomes}")
    print(f"[setup] genome_species.u32 loaded ({len(genome_to_species):,} entries)",
          file=sys.stderr)

    cache_npz = args.counts_cache_npz or (args.plots_out / "cache" / "counts_cache.npz")
    hashes_u8, func_id_arr, gnu_arr, shard_arr = load_or_build_cache(
        cache_npz, args.out_dir, args.nshards)

    # ======== PHASE 1 ========
    phase1_counts(gnu_arr, func_id_arr, hashes_u8, shard_arr,
                  func_name, figs, tbls, args)

    # ======== PHASE 2 ========
    if not args.skip_postings:
        phase2_postings(args, genome_to_species, species_id_to_name,
                        species_sizes, top_species_ids, n_genomes,
                        func_name, figs, tbls, unknown_sids)
    else:
        print("[main] skipping phase 2 (--skip_postings)", file=sys.stderr)

    # ======== PHASE 3 ========
    if args.do_coverage:
        cov_species = top_species_ids[:args.coverage_top_n]
        phase3_coverage(args, genome_to_species, species_id_to_name,
                        species_sizes, cov_species, figs, tbls)
    else:
        print("[main] skipping phase 3 (use --do_coverage to enable)",
              file=sys.stderr)

    # --- Write metadata ---
    meta = {
        "out_dir": str(args.out_dir),
        "nshards": args.nshards,
        "n_genomes": n_genomes,
        "n_species": int(len(species_sizes)),
        "n_alleles_in_cache": int(len(gnu_arr)),
        "top_species_ids": top_species_ids,
        "dominance_fraction": args.dominance_fraction,
        "include_unknown": args.include_unknown,
        "unknown_sids_found": sorted(unknown_sids),
        "min_shared_for_pair_report": args.min_shared_for_pair_report,
        "coverage_enabled": args.do_coverage,
        "coverage_fractions": args.coverage_fractions if args.do_coverage else None,
        "total_runtime_hours": (time.time() - t_global) / 3600,
        "generated_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    (args.plots_out / "run_metadata.json").write_text(
        json.dumps(meta, indent=2, default=str))

    total_h = (time.time() - t_global) / 3600
    print(f"\n[DONE] all results in {args.plots_out} — "
          f"total runtime {total_h:.1f}h", file=sys.stderr)


if __name__ == "__main__":
    main()
