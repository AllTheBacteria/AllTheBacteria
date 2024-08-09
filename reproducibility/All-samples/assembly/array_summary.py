#!/usr/bin/env python3

import argparse
import gzip
import os
import subprocess


SYLPH_COLS = [
  "Sample",
  "Run",
  "Genome_file",
  "Taxonomic_abundance",
  "Sequence_abundance",
  "Adjusted_ANI",
  "Eff_cov",
  "ANI_5-95_percentile",
  "Eff_lambda",
  "Lambda_5-95_percentile",
  "Median_cov",
  "Mean_cov_geq1",
  "Containment_ind",
  "Naive_ANI",
  "Contig_name",
  "Species",
]
SYLPH_LINE_1 = "\t".join(SYLPH_COLS)

NUCMER_COLS = [
  "[S1]",
  "[E1]",
  "[S2]",
  "[E2]",
  "[LEN 1]",
  "[LEN 2]",
  "[% IDY]",
  "[LEN R]",
  "[LEN Q]",
  "[FRM]",
  "[TAGS]",
  "[NAME R]",
  "[NAME Q]",
  "[EXTRA]",
]

NUCMER_LINE_1 = "\t".join(NUCMER_COLS)



def sample_and_run_from_o_file(filename):
    sample = None
    run = None
    with open(filename) as f:
        for line in f:
            if line.startswith("sample: "):
                sample = line.rstrip().split()[-1]
            elif line.startswith("run: "):
                run = line.rstrip().split()[-1]
    return sample, run

def load_status_file(filename):
    with open(filename) as f:
        lines = [x.rstrip() for x in f]
    assert len(lines) == 1
    return lines[0]


def load_nucmer_file(filename):
    if not os.path.exists(filename):
        return []
    with gzip.open(filename, "rt") as f:
        hits = [x.rstrip() for x in f]
    assert len(hits) > 0
    assert hits[0] == NUCMER_LINE_1
    return hits[1:]


def load_sylph_file(filename):
    if not os.path.exists(filename):
        return []
    with open(filename) as f:
        hits = [x.rstrip() for x in f]
    if len(hits) > 0:
        assert hits[0] == SYLPH_LINE_1
    return hits[1:]


parser = argparse.ArgumentParser(
    description="Make summary files from one batch of assemblies",
    usage="%(prog)s [options] <ids_file> <asm_dir> <logs_dir>",
)

parser.add_argument("ids_file", help="IDs file used for job array (sample and run accessions)")
parser.add_argument("asm_dir", help="Assembly output directory")
parser.add_argument("logs_dir", help="Logs directory")
parser.add_argument("outprefix", help="Prefix of output files")

options = parser.parse_args()



samples = {}
with open(options.ids_file) as f:
    for line in f:
        sample, run = line.rstrip().split()
        samples[len(samples) + 1] = {"sample": sample, "run": run}


logs_gz = f"{options.outprefix}.logs.gz"
nucmer_gz = f"{options.outprefix}.nucmer.gz"
sylph_gz = f"{options.outprefix}.sylph.tsv.gz"
status_gz = f"{options.outprefix}.status.gz"


sample_status = {}
sylph_no_matches = []

with gzip.open(logs_gz, "wt") as f_log, gzip.open(nucmer_gz, "wt") as f_nuc, gzip.open(sylph_gz, "wt") as f_syl, gzip.open(status_gz, "wt") as f_stat:
    print(SYLPH_LINE_1, file=f_syl)
    print(NUCMER_LINE_1, file=f_nuc)
    print("Sample", "Status", sep="\t", file=f_stat)

    for array_no in sorted(samples):
        sample = samples[array_no]["sample"]
        if ";" in sample:
            print("SKIP", sample)
            continue

        run = samples[array_no]["run"]
        o_file = f"{options.logs_dir}/{array_no}.o"
        sample_check, run_check =  sample_and_run_from_o_file(o_file)
        assert sample == sample_check
        assert run == run_check

        asm_dir = f"{options.asm_dir}/{sample}"
        status = load_status_file(os.path.join(asm_dir, "status.txt"))
        print(sample, status, sep="\t", file=f_stat)
        asm_file = os.path.join(asm_dir, f"{sample}.fa.gz")
        if status == "finished":
            assert os.path.exists(asm_file)

        nucmer = load_nucmer_file(os.path.join(asm_dir, "nucmer_human.gz"))
        if len(nucmer) > 0:
            print(*nucmer, sep="\n", file=f_nuc)

        sylph = load_sylph_file(os.path.join(asm_dir, "sylph.tsv"))
        if len(sylph) > 0:
            print(*sylph, sep="\n", file=f_syl)
        else:
            sylph_no_matches.append((sample, run))

        with open(f"{options.logs_dir}/{array_no}.e") as f_in:
            for line in f_in:
                print(sample, line, sep="\t", end="", file=f_log)

        expect_files = {"nucmer_human.gz", "status.txt", "sylph.tsv", f"{sample}.fa.gz"}
        for fname in os.listdir(asm_dir):
            if fname in expect_files:
                continue
            print("delete:", asm_dir, fname)
            subprocess.check_output(["rm", "-r", os.path.join(asm_dir, fname)])

with gzip.open(f"{options.outprefix}.sylph.no_matches.txt.gz", "wt") as f:
    for x in sylph_no_matches:
        print(*x, sep="\t", file=f)
