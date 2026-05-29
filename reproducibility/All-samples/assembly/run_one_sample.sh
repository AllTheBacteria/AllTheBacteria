#!/usr/bin/env bash

set -eu

usage() {
    echo "Usage: $0 [-d enaDataGet|sracha] root_out samples_file" >&2
}

download_method=${DOWNLOAD_METHOD:-enaDataGet}
positional=()

while [ "$#" -gt 0 ]
do
    case "$1" in
        -d|--download-method|--download_method)
            if [ "$#" -lt 2 ]
            then
                echo "ERROR: missing value for $1" >&2
                usage
                exit 1
            fi
            download_method=$2
            shift 2
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        --)
            shift
            while [ "$#" -gt 0 ]
            do
                positional+=("$1")
                shift
            done
            ;;
        -*)
            echo "ERROR: unknown option: $1" >&2
            usage
            exit 1
            ;;
        *)
            positional+=("$1")
            shift
            ;;
    esac
done

if [ "${#positional[@]}" -ne 2 ]
then
    usage
    exit 1
fi

root_out=${positional[0]}
samples_file=${positional[1]}

case "$download_method" in
    enaDataGet|sracha) ;;
    *)
        echo "ERROR: download_method must be enaDataGet or sracha. Got: $download_method" >&2
        exit 1
        ;;
esac

echo "SLURM_ARRAY_TASK_ID: $SLURM_ARRAY_TASK_ID"

a=$(awk "NR==$SLURM_ARRAY_TASK_ID" "$samples_file")
sample=$(echo "$a" | cut -d" " -f1)
run=$(echo "$a" | cut -d" " -f2)

echo "sample: $sample"
echo "run: $run"
echo "download_method: $download_method"


/FIX_PATH/process_one_sample.py \
    --run "$run" \
    --sample "$sample" \
    --download_method "$download_method" \
    --out "$root_out/$sample" \
    --syldb /FIX_PATH/v0.3-c200-gtdb-r214.syldb \
    --shov_img /FIX_PATH/shovill.1.1.0-2022Dec.img \
    --nuc_script /FIX_PATH/nucmer_splitter.py \
    --nuc_dir /FIX_PATH/GCA_009914755.split_ref \
    --file2species /FIX_PATH/gtdb_r214.syldb.file2species.map
