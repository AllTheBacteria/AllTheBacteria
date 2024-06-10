#!/usr/bin/bash

set -eu

split_files_dir=/FIX_PATH/
root_out=/FIX_PATH/

index=$SLURM_ARRAY_TASK_ID
outdir=$root_out/$index
ids_file=$split_files_dir/$index

echo "Running prefetch on batch number $index. Outdir: $outdir"

if [ ! -d $outdir ]
then
    mkdir $outdir
fi

cd $outdir
prefetch --option-file $ids_file &> prefetch.stdouterr

