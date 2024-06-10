#!/usr/bin/env python3

import argparse
import os
import subprocess
import sys
import time

# SPLIT_ROOT = full path to the directory of "split input files".
# Files must be called 1, 2, 3, 4,  ...
# File N is processed by element N of the job array.
# Each file is tab-delimited, no header line, and has two fields:
# 1) sample name 2) full path to assembly fasta file
SPLIT_ROOT = "FIX_PATH"

ROOT_OUT = "FIX_PATH" # root directory of output checkm2 files
IMG = "/FIX_PATH/checkm2.1.0.1--pyh7cba7a3_0.img" # checkm2 singularity container
DB = "/FIX_PATH/uniref100.KO.1.dmnd"  # checkm2 database
CHECKM2 = f"singularity exec {IMG} checkm2 predict --allmodels --lowmem --database_path {DB} --remove_intermediates"
CHECKM2_COLS = [
    "Name",
    "Completeness_General",
    "Contamination",
    "Completeness_Specific",
    "Completeness_Model_Used",
    "Translation_Table_Used",
    "Coding_Density",
    "Contig_N50",
    "Average_Gene_Length",
    "Genome_Size",
    "GC_Content",
    "Total_Coding_Sequences",
    "Additional_Notes",
]

def get_array_index():
    array_index = os.environ.get("LSB_JOBINDEX", None)
    if array_index is None:
        array_index = os.environ.get("SLURM_ARRAY_TASK_ID", None)
    if array_index is None:
        raise Exception("LSB_JOBINDEX/SLURM_ARRAY_TASK_ID not in env. Cannot continue")
    return array_index


def fix_sample_name_in_report_tsv(sample, infile, outfile):
    with open(infile) as f:
        results = [x.rstrip().split("\t") for x in f]
        if len(results) != 2:
            print("ERROR LINES!=2 IN RESULTS", sample, flush=True)
            return False
        if results[0] != CHECKM2_COLS:
            print("ERROR Unexpected column names", sample, flush=True)
            return False
        if len(results[1]) != len(CHECKM2_COLS):
            print("ERROR wrong number of fields in second line of results", sample, flush=True)
            return False

    with open(outfile, "w") as f:
        print(sample, *results[1][1:], sep="\t", file=f)

    return True


def run_one_sample(sample, fasta_file):
    done_file = f"{sample}.done"
    if os.path.exists(done_file):
        print("Already done", sample, flush=True)
        return True

    fail_file = f"{sample}.fail"
    if os.path.exists(fail_file):
        print("Already fail", sample, flush=True)
        return False

    subprocess.check_output(f"rm -rf {sample} {sample}.tsv", shell=True)

    command = f"{CHECKM2} -i {fasta_file} -o {sample}"
    print(command, flush=True)
    try:
        subprocess.check_output(command, shell=True, timeout=2400)
    except:
        print("ERROR RUNNING CHECKM", sample, flush=True)
        return False

    result_file = os.path.join(sample, "quality_report.tsv")
    if not os.path.exists(result_file):
        print("ERROR NO RESULT FILE", sample, flush=True)
        return False

    outfile = f"{sample}.tsv"
    try:
        ok = fix_sample_name_in_report_tsv(sample, result_file, outfile)
    except:
        print("ERROR parsing checkm output file", sample, flush=True)
        return False

    if not ok:
        print("ERROR parsing checkm output file", sample, flush=True)
        return False

    subprocess.check_output(f"rm -rf {sample}", shell=True)
    subprocess.check_output(f"touch {sample}.done", shell=True)
    return True




job_array_index = get_array_index()


samples_file = os.path.join(SPLIT_ROOT, job_array_index)
with open(samples_file) as f:
    samples = [x.rstrip().split() for x in f]


outdir = os.path.join(ROOT_OUT, job_array_index)
if not os.path.exists(outdir):
    os.mkdir(outdir)

os.chdir(outdir)

all_done_file = "all.done"
if os.path.exists(all_done_file):
    print("All done already")
    sys.exit()

results_files = []
fails = []

for sample, query_file in samples:
    assert sample != "all"
    try:
        ok = run_one_sample(sample, query_file)
    except:
        print("ERROR OTHER", sample, flush=True)
        ok = False

    if not ok:
        fails.append(sample)
        continue

    results_file = f"{sample}.tsv"
    if os.path.exists(results_file):
        results_files.append(results_file)
    else:
        fails.append(sample)


if len(fails):
    with open("fails.txt", "w") as f_out:
        print(*fails, sep="\n", file=f_out)



if len(results_files) > 0:
    with open("all.tsv", "w") as f_out:
        print(*CHECKM2_COLS, sep="\t", file=f_out)
        for filename in results_files:
            with open(filename) as f_in:
                for line in f_in:
                    print(line, end="", file=f_out)


with open(all_done_file, "w") as f:
    pass

for sample, query_file in samples:
    print("deleting intermediate files", sample)
    command = f"rm -rf {sample} {sample}.bin_input {sample}.tsv {sample}.done"
    try:
        subprocess.check_output(command, shell=True)
    except:
        time.sleep(5)
        subprocess.run(command, shell=True)

