#!/bin/bash
#SBATCH --job-name=atb_wget
#SBATCH --output=atb_dl_%A_%a.out
#SBATCH --error=atb_dl_%A_%a.err
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --time=24:00:00

set -euo pipefail

TSV="atb.tsv"   # <-- put atb.tsv in the same directory, or change to full path
OUTROOT="ATB/atb_bakta_downloads"
DL="${OUTROOT}/downloads"
MANI="${OUTROOT}/manifest_parts"

mkdir -p "${DL}" "${MANI}"

# Extract filename/url/md5 from the TSV for this array task.
# Assumes header includes: filename, url, md5
LINE=$(awk -F $'\t' -v tid="${SLURM_ARRAY_TASK_ID}" '
  NR==1{
    for(i=1;i<=NF;i++){h[$i]=i}
    next
  }
  NR==(tid+1){
    f=$(h["filename"]); u=$(h["url"]); m=$(h["md5"]);
    gsub(/[ \r\n\t]/,"",m);
    print f"\t"u"\t"tolower(m);
    exit
  }
' "${TSV}")

if [[ -z "${LINE}" ]]; then
  echo "[ERROR] Could not find line for task ${SLURM_ARRAY_TASK_ID} in ${TSV}" >&2
  exit 2
fi

IFS=$'\t' read -r FNAME URL MD5 <<< "${LINE}"
TAR="${DL}/${FNAME}"

echo "[INFO] task=${SLURM_ARRAY_TASK_ID} downloading ${FNAME}"
echo "[INFO] url=${URL}"

# Download with retry + resume
wget -q --show-progress --tries=10 --waitretry=10 -c -O "${TAR}" "${URL}"

# MD5 check
OBS=$(md5sum "${TAR}" | awk '{print tolower($1)}')
MATCH="NO"
[[ "${OBS}" == "${MD5}" ]] && MATCH="YES"

SIZE=$(stat -c '%s' "${TAR}")

# Write a per-task manifest line (optional but useful)
OUT="${MANI}/part_${SLURM_ARRAY_TASK_ID}.tsv"
echo -e "filename\turl\texpected_md5\tobserved_md5\tmd5_match\tsize_bytes" > "${OUT}"
echo -e "${FNAME}\t${URL}\t${MD5}\t${OBS}\t${MATCH}\t${SIZE}" >> "${OUT}"

echo "[DONE] ${FNAME} md5_match=${MATCH} size_bytes=${SIZE}"
