#!/usr/bin/env python3
"""
assign_ids_by_species.py

Reads a TSV with columns:
  Sample   Species   HQ

Assigns:
- SpeciesID (largest species first), BUT forces an "unknown" category to the end
- SampleID (after sorting by SpeciesID then Sample)

Outputs:
1) samples_with_ids.tsv
   SampleID  Sample  SpeciesID  Species  HQ

2) species_stats.tsv
   SpeciesID  Species  n_samples  n_HQ_T  n_HQ_F

Also prints summary stats to stdout.

New features added:
- --unknown_labels: comma-separated list of species labels to treat as "unknown" and put LAST
  (default includes common variants)
- --include_samples: file with one Sample per line; keep only those samples (after optional HQ filter)

Usage:
  python assign_ids_by_species.py --in samples.tsv --out_dir out

Keep only HQ == T and only a specific inclusion list:
  python assign_ids_by_species.py --in samples.tsv --out_dir out --hq_only T --include_samples include.txt

Force a specific unknown label:
  python assign_ids_by_species.py --in samples.tsv --out_dir out --unknown_labels "unknown,Unclassified"
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Optional, Set

import pandas as pd


DEFAULT_UNKNOWN_LABELS = {
    "unknown",
    "Unknown",
    "unclassified",
    "Unclassified",
    "NA",
    "N/A",
    "na",
    "",
}


def load_inclusion_list(path: Path) -> Set[str]:
    inc: Set[str] = set()
    with path.open("rt", encoding="utf-8") as f:
        for line in f:
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            inc.add(s)
    return inc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="infile", required=True, help="Input TSV with Sample, Species, HQ columns.")
    ap.add_argument("--out_dir", required=True, help="Output directory.")
    ap.add_argument("--hq_only", default=None, help='If set (e.g., "T"), keep only rows with HQ == this value.')
    ap.add_argument("--sep", default="\t", help="Input separator (default: tab).")

    ap.add_argument(
        "--include_samples",
        default=None,
        help="Optional file with one Sample per line. If provided, only those samples are kept.",
    )
    ap.add_argument(
        "--unknown_labels",
        default='unknown',
        help=(
            "Comma-separated list of Species labels to treat as 'unknown' and force to the END "
            "(e.g., 'unknown,Unclassified'). Default covers common variants."
        ),
    )

    args = ap.parse_args()

    inpath = Path(args.infile)
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Unknown labels
    if args.unknown_labels:
        unknown_labels = {x.strip() for x in args.unknown_labels.split(",")}
    else:
        unknown_labels = set(DEFAULT_UNKNOWN_LABELS)

    # Inclusion list
    include_set: Optional[Set[str]] = None
    if args.include_samples:
        include_set = load_inclusion_list(Path(args.include_samples))

    # Read
    df = pd.read_csv(inpath, sep=args.sep, dtype=str)
    required = {"Sample", "Species", "HQ"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"ERROR: Missing required columns: {sorted(missing)}. Found: {list(df.columns)}")

    # Clean
    df["Sample"] = df["Sample"].astype(str).str.strip()
    df["Species"] = df["Species"].astype(str).str.strip()
    df["HQ"] = df["HQ"].astype(str).str.strip()

    # Optional inclusion filter (apply early)
    if include_set is not None:
        df = df[df["Sample"].isin(include_set)].copy()

    # Optional HQ filter
    if args.hq_only is not None:
        df = df[df["HQ"] == args.hq_only].copy()

    if df.empty:
        raise SystemExit("ERROR: No rows left after filtering (include_samples / hq_only).")

    # Flag unknown species
    # (exact match against labels; include empty string in defaults)
    df["_is_unknown"] = df["Species"].isin(unknown_labels)

    # Compute species counts
    species_counts = (
        df.groupby("Species", dropna=False)
        .size()
        .reset_index(name="n_samples")
    )
    species_counts["_is_unknown"] = species_counts["Species"].isin(unknown_labels)

    # Sort species: (unknown last) then by n_samples desc then Species name
    species_counts = (
        species_counts.sort_values(
            by=["_is_unknown", "n_samples", "Species"],
            ascending=[True, False, True],
        )
        .reset_index(drop=True)
    )

    # Assign SpeciesID
    species_counts["SpeciesID"] = range(1, len(species_counts) + 1)
    species_to_id = dict(zip(species_counts["Species"], species_counts["SpeciesID"]))

    # Attach SpeciesID
    df["SpeciesID"] = df["Species"].map(species_to_id).astype("int64")

    # Sort rows by SpeciesID then Sample (stable)
    df = df.sort_values(["SpeciesID", "Sample"], ascending=[True, True]).reset_index(drop=True)

    # Assign SampleID in this sorted order
    df.insert(0, "SampleID", range(1, len(df) + 1))

    # Stats per species with HQ breakdown
    hq_t = (df["HQ"] == "T").astype(int)
    hq_f = (df["HQ"] == "F").astype(int)

    species_stats = (
        df.assign(_HQ_T=hq_t, _HQ_F=hq_f)
        .groupby(["SpeciesID", "Species"], as_index=False)
        .agg(
            n_samples=("SampleID", "count"),
            n_HQ_T=("_HQ_T", "sum"),
            n_HQ_F=("_HQ_F", "sum"),
        )
        .merge(
            species_counts[["Species", "_is_unknown"]], on="Species", how="left"
        )
        .sort_values("SpeciesID")
        .reset_index(drop=True)
    )

    # Outputs
    out_samples = out_dir / "samples_with_ids.tsv"
    out_species = out_dir / "species_stats.tsv"

    df_out = df[["SampleID", "Sample", "SpeciesID", "Species", "HQ"]]
    df_out.to_csv(out_samples, sep="\t", index=False)
    species_stats[["SpeciesID", "Species", "n_samples", "n_HQ_T", "n_HQ_F"]].to_csv(out_species, sep="\t", index=False)

    # Summary
    n_species = len(species_stats)
    n_samples = len(df_out)

    unknown_in_stats = species_stats[species_stats["Species"].isin(unknown_labels)]
    unknown_note = ""
    if not unknown_in_stats.empty:
        unknown_row = unknown_in_stats.iloc[0]
        unknown_note = f" | unknown='{unknown_row['Species']}' has {int(unknown_row['n_samples']):,} samples and was forced to the end"

    print("Done.")
    print(f"Input: {inpath}")
    print(f"Output: {out_dir}")
    if include_set is not None:
        print(f"Inclusion list: {args.include_samples} (kept {n_samples:,} rows after filtering)")
    print(f"Total samples: {n_samples:,}")
    print(f"Total species: {n_species:,}{unknown_note}")

    print("\nTop 5 species by sample count (after unknown-last rule):")
    top5 = species_stats.sort_values(["n_samples", "Species"], ascending=[False, True]).head(5)[["SpeciesID", "Species", "n_samples"]]
    print(top5.to_string(index=False))

    print("\nLast 5 species (check unknown is last):")
    last5 = species_stats.tail(5)[["SpeciesID", "Species", "n_samples"]]
    print(last5.to_string(index=False))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
