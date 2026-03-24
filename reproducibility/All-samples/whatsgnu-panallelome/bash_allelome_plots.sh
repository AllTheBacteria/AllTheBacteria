#!/bin/bash
#SBATCH -J allelome_analysis
#SBATCH -c 8
#SBATCH --mem=500G
#SBATCH -t 200:00:00
#SBATCH -o allelome_%j.out
#SBATCH -e allelome_%j.err

set -euo pipefail

OUT="WGNU_ATB_DB"
SAMPLES="allthebacteria/samples_with_ids.tsv"
RESULTS="ATB_summary_figures_tables"
SPECIES="allthebacteria/species_stats.tsv"
FUNCTIONS="allthebacteria/WGNU_ATB_DB/metadata/functions.tsv.gz"

mkdir -p "${RESULTS}/cache"

# Step 1: cache (if not already built)
if [ ! -f "${RESULTS}/cache/counts_cache.npz" ]; then
    python allthebacteria/build_allelome_cache.py \
        --counts_root "${OUT}/lmdb_counts" \
        --nshards 8 \
        --cache_npz "${RESULTS}/cache/counts_cache.npz"
fi

# Step 2+3: all analyses including coverage
python allthebacteria/allelome_plots_v5.py \
    --out_dir "${OUT}" \
    --samples_with_ids_tsv "${SAMPLES}" \
    --nshards 8 \
    --plots_out "${RESULTS}" \
    --species_stats_tsv "${SPECIES}" \
    --functions_tsv_gz "${FUNCTIONS}" \
    --do_coverage \
    --coverage_fractions 0.90,0.99 \
    --dominance_fraction 0.90
