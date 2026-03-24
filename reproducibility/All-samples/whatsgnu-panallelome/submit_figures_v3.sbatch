#!/bin/bash
#SBATCH --job-name=ATB_figures
#SBATCH --output=ATB_figures_%j.out
#SBATCH --error=ATB_figures_%j.err
#SBATCH --time=20:00:00
#SBATCH --cpus-per-task=6
#SBATCH --mem=120G

# ── Variables ──────────────────────────────────────────────────────────────────
SAMPLES_TSV="allthebacteria/samples_with_ids.tsv"
Tables="allthebacteria/ATB_summary_figures_tables/tables"
Figures="allthebacteria/ATB_summary_figures_tables/publication_figures"
Sp_Stats="allthebacteria/species_stats.tsv"
records_faa="allthebacteria/ATB_hash_seq/records_per_faa.tsv"
cache_npz_file="allthebacteria/ATB_summary_figures_tables/cache/counts_cache.npz"
SCRIPT="allthebacteria/allelome_publication_plots_v2.py"
# ──────────────────────────────────────────────────────────────────────────────

echo "Job $SLURM_JOB_ID started on $SLURM_NODELIST at $(date)"


python ${SCRIPT} \
    --tables_dir        ${Tables} \
    --figures_dir       ${Figures} \
    --samples_tsv       ${SAMPLES_TSV} \
    --species_stats_tsv ${Sp_Stats} \
    --records_per_faa   ${records_faa} \
    --cache_npz         ${cache_npz_file} \
    --top_n_species 80 \
    --top_n_label 30 \
    --top_n_heatmap 30 \
    --top_n_network 20 \
    --top_n_violin 50 \
    --min_shared_network 1000 \
    --dpi 300

echo "Job finished at $(date) with exit code $?"

