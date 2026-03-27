#!/bin/bash
#SBATCH --job-name=hash_seq_table
#SBATCH --output=hash_seq_table_%j.out
#SBATCH --error=hash_seq_table_%j.err
#SBATCH --time=40:00:00
#SBATCH --cpus-per-task=6
#SBATCH --mem=250G

# ── Variables ──────────────────────────────────────────────────────────────────
SAMPLES_TSV="/mnt/isilon/allthebacteria/samples_with_ids.tsv"
FAA_DIR="/mnt/isilon/allthebacteria/faa/"
OUT_DIR="/mnt/isilon/allthebacteria/ATB_hash_seq"
SCRIPT="/mnt/isilon/allthebacteria/build_hash_sequence_table_v4.py"
# ──────────────────────────────────────────────────────────────────────────────

echo "Job $SLURM_JOB_ID started on $SLURM_NODELIST at $(date)"

# Auto-detect resume
RESUME_FLAG=""
if [ -f "${OUT_DIR}/checkpoint.txt" ]; then
    DONE=$(wc -l < "${OUT_DIR}/checkpoint.txt")
    TOTAL=$(tail -n +2 ${SAMPLES_TSV} | wc -l)
    echo "Checkpoint found: ${DONE}/${TOTAL} samples already processed - resuming"
    RESUME_FLAG="--resume"
else
    echo "No checkpoint found - starting fresh"
fi

python ${SCRIPT} \
    --samples_tsv ${SAMPLES_TSV} \
    --faa_dir ${FAA_DIR} \
    --out_dir ${OUT_DIR} \
    --memory_efficient \
    --checkpoint_interval 100 \

echo "Job finished at $(date) with exit code $?"
