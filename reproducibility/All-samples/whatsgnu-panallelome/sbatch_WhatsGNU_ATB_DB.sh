#!/bin/bash
#SBATCH --job-name=WGNU_ATB_DB
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=40
#SBATCH --mem=250G
#SBATCH --time=144:00:00
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --output=logs/WGNU_ATB_DB.%j.out
#SBATCH --error=logs/WGNU_ATB_DB.%j.err

set -euo pipefail

module purge
# module load python/3.11

export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MKL_NUM_THREADS=1
export NUMEXPR_NUM_THREADS=1

SAMPLE_TABLE=allthebacteria/samples_with_ids.tsv
FAA_DIR=allthebacteria/faa   # shared allthebacteria storage
OUT_DIR=allthebacteria/WGNU_ATB_DB
TMP_DIR=/scr1/users/$USER/WGNU_tmp_$SLURM_JOB_ID
LOG_FILE=$OUT_DIR/build.log

mkdir -p "$OUT_DIR" "$TMP_DIR" logs

python WhatsGNU_ATB_DB.py \
  --sample_table "$SAMPLE_TABLE" \
  --faa_dir "$FAA_DIR" \
  --out_dir "$OUT_DIR" \
  --tmp_dir "$TMP_DIR" \
  --shards 8 \
  --with_postings \
  --sort_mem_mb 98304 \
  --lmdb_map_gb_counts_per_shard 48 \
  --lmdb_map_gb_postings_per_shard 320 \
  --log_file "$LOG_FILE" \
  --log_level INFO


echo "Done"
