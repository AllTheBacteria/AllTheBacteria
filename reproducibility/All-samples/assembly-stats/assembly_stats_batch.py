#!/usr/bin/env python3

import argparse
import csv
import os
import sys
import subprocess


STATS_COLS = [
    "sample",
    "total_length",
    "number",
    "mean_length",
    "longest",
    "shortest",
    "N_count",
    "Gaps",
    "N50",
    "N50n",
    "N70",
    "N70n",
    "N90",
    "N90n",
]


def parse_stats_stdout(p, sample, filename):
    fields = p.stdout.strip().split("\t")
    assert fields[0] == filename
    assert len(fields) == len(STATS_COLS)
    fields[0] = sample
    return "\t".join(fields)


RELEASE_ROOT = "FIX_PATH"
TSV = f"FIX_PATH/sample_path.tsv"

parser = argparse.ArgumentParser(
    description="description",
    usage="%(prog)s <start> <end> <outfile>",
)
parser.add_argument("start", type=int, help="start line of sample_path.tsv file")
parser.add_argument("end", type=int, help="end line of sample_path.tsv file")
parser.add_argument("outfile", help="output file")

options = parser.parse_args()

with open(TSV) as f_in, open(options.outfile, "w") as f_out:
    print(*STATS_COLS, sep="\t", file=f_out)

    for i, d in enumerate(csv.DictReader(f_in, delimiter="\t")):
        if i < options.start:
            continue
        if i > options.end:
            break

        fa = os.path.join(RELEASE_ROOT, d["Path"])
        p = subprocess.run(["assembly-stats", "-u", fa], stdout=subprocess.PIPE, universal_newlines=True)
        if p.returncode != 0:
            print("Error", d, file=sys.stderr)
            continue

        try:
            to_print = parse_stats_stdout(p, d["Sample"], fa)
        except:
            print("Error", d, file=sys.stderr)
            continue

        print(to_print, file=f_out)
