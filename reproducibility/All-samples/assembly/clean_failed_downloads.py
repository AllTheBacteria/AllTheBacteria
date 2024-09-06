#!/usr/bin/env python3

import argparse
import os
import subprocess

def dl_error_from_e_file(filename):
    if not os.path.exists(e_file):
        return False

    with open(filename) as f:
        lines = [x.strip() for x in f]

    return len(lines) > 0 and "Exception: Error downloading reads. Stopping" in lines



parser = argparse.ArgumentParser(
    description="description",
    usage="%(prog)s [options] <ids_file> <asm_dir> <logs_dir>",
)
parser.add_argument("ids_file", help="Split ids file used for job array")
parser.add_argument("asm_dir", help="Assembly output directory")
parser.add_argument("logs_dir", help="Logs directory")

options = parser.parse_args()

samples = {}
with open(options.ids_file) as f:
    for line in f:
        sample, run = line.rstrip().split()
        samples[len(samples) + 1] = {"sample": sample, "run": run}

error_indexes = []

dirs_to_delete = []
files_to_delete = []

for array_no in sorted(samples):
    e_file = f"{options.logs_dir}/{array_no}.e"
    dl_err = dl_error_from_e_file(e_file)
    if not dl_err:
        continue

    sample = samples[array_no]["sample"]

    asm_dir = f"{options.asm_dir}/{sample}"
    assert os.path.exists(asm_dir)
    dirs_to_delete.append(asm_dir)
    o_file = f"{options.logs_dir}/{array_no}.o"
    assert os.path.exists(o_file)
    files_to_delete.append(o_file)
    files_to_delete.append(e_file)

    error_indexes.append(array_no)


if len(error_indexes) < 20:
    print(",".join(str(x) for x in error_indexes))
else:
    start = end = error_indexes[0]
    to_print = []

    for i in error_indexes[1:]:
        if i == end + 1:
            end += 1
        else:
            if start == end:
                to_print.append(str(start))
            else:
                to_print.append(f"{start}-{end}")
            start = end = i

    if start == end:
        to_print.append(str(start))
    else:
        to_print.append(f"{start}-{end}")

    print(*to_print, sep=",")


for x in dirs_to_delete:
    command = f"rm -r {x}"
    subprocess.check_output(command, shell=True)

for x in files_to_delete:
    command = f"rm {x}"
    subprocess.check_output(command, shell=True)

