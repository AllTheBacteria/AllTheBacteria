#!/usr/bin/env bash

set -eu

root_out=$1
samples_file=$2
echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"

a=$(awk "NR==$SLURM_ARRAY_TASK_ID" $samples_file)
sample=$(echo $a | cut -d" " -f1)
run=$(echo $a | cut -d" " -f2)

echo "sample: $sample"
echo "run: $run"


/FIX_PATH/process_one_sample.py \
    --run $run \
    --sample $sample \
    --out $root_out/$sample \
    --syldb /FIX_PATH/v0.3-c200-gtdb-r214.syldb \
    --shov_img /FIX_PATH/shovill.1.1.0-2022Dec.img \
    --nuc_script /FIX_PATH/nucmer_splitter.py \
    --nuc_dir /FIX_PATH/GCA_009914755.split_ref \
    --file2species /FIX_PATH/gtdb_r214.syldb.file2species.map
