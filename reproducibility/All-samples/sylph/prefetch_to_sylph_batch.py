#!/usr/bin/env python3

import argparse
import json
import os
import re
import subprocess

success_re = re.compile(r""" '(?P<run>.*)\.sralite' was downloaded successfully""")
success_re2 = re.compile(r""" '(?P<run>.*)\.lite' was downloaded successfully""")
success_re3 = re.compile(r""" '(?P<run>.*)' was downloaded successfully""")
success_re4 = re.compile(r""" '(?P<run>.*)\.sralite' is found locally""")
success_re5 = re.compile(r""" '(?P<run>.*)\.lite' is found locally""")
success_re6 = re.compile(r""" '(?P<run>.*)' is found locally""")
failed_acc_re = re.compile(r"""err: name not found while resolving query within virtual file system module - failed to resolve accession '(?P<run>.*)' - no data""")

REGEXES = {
    success_re: {"success": True, "fail_reason": "NA"},
    success_re2: {"success": True, "fail_reason": "NA"},
    success_re3: {"success": True, "fail_reason": "NA"},
    success_re4: {"success": True, "fail_reason": "NA"},
    success_re5: {"success": True, "fail_reason": "NA"},
    success_re6: {"success": True, "fail_reason": "NA"},
    failed_acc_re: {"success": False, "fail_reason": "failed to resolve accession"},
}


SYLPH_DB = "/FIX_PATH/v0.3-c200-gtdb-r214.syldb"
OUT_ROOT = "/FIX_PATH/"
SPLIT_ROOT = "/FIX_PATH/"

def parse_stdouterr_file(infile):
    results = {}
    with open(prefetch_e) as f:
        for line in f:
            for regex, d in REGEXES.items():
                match = regex.search(line)
                if match is not None:
                    print("MATCH!", line)
                    run = match.group("run")
                    results[run] = [d["success"], d["fail_reason"]]
                    break
        return results



def process_one_run(indir, run_id):
    command = f"fasterq-dump --fasta --split-3 {run_id}"
    print("command", command)

    try:
        print("to_fasta", run_id, command, flush=True)
        subprocess.check_output(command, shell=True, cwd=indir)
    except:
        return False, "fail_fasterq-dump"

    fasta_1 = os.path.join(indir, f"{run_id}_1.fasta")
    fasta_2 = os.path.join(indir, f"{run_id}_2.fasta")
    if not (os.path.exists(fasta_1) and os.path.exists(fasta_2)):
        return False, "fail_not_all_fasta_files_made"

    try:
        tmp_out = os.path.join(indir, f"{run_id}.tmp.sketch")
        subprocess.check_output(f"rm -rf {tmp_out}", shell=True)
        subprocess.check_output(f"sylph sketch -1 {fasta_1} -2 {fasta_2} -d {tmp_out}", shell=True)
        outfile = os.path.join(indir, f"{run_id}.sylph.tsv")
        subprocess.check_output(f"sylph profile -t 1 {SYLPH_DB} {tmp_out}/*.sylsp > {outfile}", shell=True)
        subprocess.check_output(f"rm -rf {tmp_out}", shell=True)
    except:
        return False, "error_sylph"

    print("Done OK", run_id)
    return True, "NA"



parser = argparse.ArgumentParser(
    description="Run sylph on dir from running prefetch on a file of run IDs",
    usage="%(prog)s",
)
options = parser.parse_args()

job_array_index = os.environ.get("LSB_JOBINDEX", None)
if job_array_index is None:
    job_array_index = os.environ.get("SLURM_ARRAY_TASK_ID", None)

if job_array_index is None:
    raise Exception("LSB_JOBINDEX/SLURM_ARRAY_TASK_ID not in env. Cannot continue")
options.ids_file = os.path.join(SPLIT_ROOT, f"{job_array_index}")

indir = os.path.join(OUT_ROOT, job_array_index)
assert os.path.exists(indir)

assert os.path.exists(options.ids_file)
with open(options.ids_file) as f:
    all_runs = [x.rstrip() for x in f]
all_runs.sort()


status_file = os.path.join(indir, "sylph_status.json")
if os.path.exists(status_file):
    with open(status_file) as f:
        sylph_results = json.load(f)
else:
    sylph_results = {}


prefetch_e = os.path.join(indir, "prefetch.stdouterr")
assert os.path.exists(prefetch_e)

print("Total runs:", len(all_runs), flush=True)
prefetch_results = parse_stdouterr_file(prefetch_e)
print(prefetch_results)

for run in all_runs:
    sylph_status = sylph_results.get(run, (False, "unknown"))
    prefetch_status = prefetch_results.get(run, (False, "unknown"))

    if sylph_status[0]:
        print(run, "already done", flush=True)
    elif prefetch_status[0]:
        sylph_results[run] = process_one_run(indir, run)
    else: # failed for some reason
        sylph_results[run] = False, prefetch_status[1]

    sylph_status = sylph_results.get(run, (False, "unknown"))
    if sylph_status[0]:
        try:
            subprocess.check_output(f"rm -rf {run} {run}_?.fasta", cwd=indir, shell=True)
        except:
            sylph_results[run] = False, "error_cleaning_files"


    with open(status_file, "w") as f:
        json.dump(sylph_results, f, indent=2)
