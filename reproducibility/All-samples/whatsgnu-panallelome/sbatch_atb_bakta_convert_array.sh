#!/bin/bash
#SBATCH --job-name=atb_bakta_conv
#SBATCH --output=ATB/atb_bakta_convert/logs/conv_%A_%a.out
#SBATCH --error=ATB/atb_bakta_convert/logs/conv_%A_%a.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=12
#SBATCH --mem=64G
#SBATCH --time=72:00:00

set -euo pipefail

# ---- EDIT THESE ----
SCRATCH_ROOT="ATB/atb_bakta_convert"
DL_DIR="ATB/atb_bakta_downloads/downloads"
FINAL_OUT="allthebacteria"
PY="ATB/atb_bakta_pipeline_v2.py"   # or the full path where you put it
# --------------------

ARGS_FILE="${SCRATCH_ROOT}/args/args_chunks"
CHUNK_FILE=$(sed -n "${SLURM_ARRAY_TASK_ID}p" "${ARGS_FILE}")

TASK_OUT="${SCRATCH_ROOT}/tasks/task_$(printf "%06d" "${SLURM_ARRAY_TASK_ID}")"
mkdir -p "${TASK_OUT}"

echo "[INFO] task=${SLURM_ARRAY_TASK_ID} chunk=${CHUNK_FILE}"
echo "[INFO] downloads=${DL_DIR}"
echo "[INFO] scratch=${TASK_OUT}"
echo "[INFO] final=${FINAL_OUT}"

srun python "${PY}" \
  --jobs-file "${CHUNK_FILE}" \
  --scratch-out "${TASK_OUT}" \
  --final-out "${FINAL_OUT}" \
  --downloads-dir "${DL_DIR}" \
  --jobs 10
