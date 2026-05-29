#!/usr/bin/env bash

set -vexu

# Edit the paths in these 3 lines
samples_runs_file=/FIX_PATH/sample_and_runs_file
asm_dir=/FIX_PATH/assemblies
logs_dir=/FIX_PATH/logs

# Override with DOWNLOAD_METHOD=sracha ./run_one_lsf_array.sh
download_method=${DOWNLOAD_METHOD:-enaDataGet}

mkdir -p "$asm_dir"
mkdir -p "$logs_dir"

bsub \
    -R "select[mem>18000] rusage[mem=18000]" -M18000 \
    -W 1000 \
    -o "$logs_dir/%I.o" \
    -e "$logs_dir/%I.e" \
    -J "atb_assembly[1-4000]%50" \
    ./run_one_sample.sh -d "$download_method" "$asm_dir" "$samples_runs_file" LSF
