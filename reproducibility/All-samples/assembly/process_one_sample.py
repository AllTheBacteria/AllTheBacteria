#!/usr/bin/env python3

import argparse
import csv
import gzip
import hashlib
import logging
import os
import requests
import subprocess
import pyfastaq
import random
import time


def set_status(filename, status):
    with open(filename, "w") as f:
        print(status, file=f)


def get_ena_metadata(run_id):
    wanted_fields = ["run_accession", "fastq_md5", "fastq_ftp"]
    url = "http://www.ebi.ac.uk/ena/portal/api/filereport?"
    data = {
        "accession": run_id,
        "result": "read_run",
        "fields": ",".join(wanted_fields),
    }
    logging.info(f"Getting metadata from ENA for run {run_id}")
    try:
        r = requests.get(url, data)
    except:
        raise Exception(f"Error querying ENA to get sample from run {run_id} {r.url}")

    if r.status_code != requests.codes.ok:
        raise Exception(
            f"Error requesting data. Error code: {r.status_code}. URL:  {r.url}"
        )

    lines = r.text.rstrip().split("\n")
    if len(lines) != 2:
        lines_str = "\n".join(lines)
        raise Exception(f"Expected exactly 2 lines from ENA request. Got: {lines_str}")

    lines = [x.rstrip().split("\t") for x in lines]
    result = dict(zip(*lines))
    logging.info(f"Metadata: {result}")
    return result


def md5_from_meta(meta):
    files = meta["fastq_ftp"].split(";")
    md5s = meta["fastq_md5"].split(";")
    assert len(files) == len(md5s)
    md5_1 = None
    md5_2 = None
    for fname, md5 in zip(files, md5s):
        if fname.endswith("_1.fastq.gz"):
            md5_1 = md5
        elif fname.endswith("_2.fastq.gz"):
            md5_2 = md5
    assert md5_1 is not None
    assert md5_2 is not None
    return md5_1, md5_2


def get_md5_of_file(filename):
    hash_md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(1048576), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()


def download_reads(run_accession):
    command = ["enaDataGet", "-f", "fastq", run_accession]
    logging.info("run: " + " ".join(command))
    try:
        subprocess.check_output(command)
    except:
        raise Exception("Error downloading reads")

    fq1 = os.path.join(run_accession, f"{run_accession}_1.fastq.gz")
    fq2 = os.path.join(run_accession, f"{run_accession}_2.fastq.gz")
    if not os.path.exists(fq1) and os.path.exists(fq2):
        subprocess.check_output(["rm", "-rf", run_accession])
        raise Exception("Error downloading reads")

    # enaDataGet can have errors but return zero. Check the md5 of each file
    try:
        ena_meta = get_ena_metadata(run_accession)
        md5_1, md5_2 = md5_from_meta(ena_meta)
    except:
        raise Exception("Error getting ENA metadata")

    if get_md5_of_file(fq1) != md5_1:
        raise Exception(f"Error md5 mismatch fastq file 1 {fq1}")
    logging.info(f"md5 ok {fq1} {md5_1}")

    if get_md5_of_file(fq2) != md5_2:
        raise Exception(f"Error md5 mismatch fastq file 2 {fq2}")
    logging.info(f"md5 ok {fq2} {md5_2}")

    return fq1, fq2


def gzip_check(filename):
    try:
        command = ["gzip", "-t", filename]
        logging.info("Checking valid gzip: " + " ".join(command))
        subprocess.check_output(command)
    except:
        logging.info(f"Failed gzip test: {filename}")
        return False

    logging.info(f"Passed gzip test: {filename}")
    return True


def load_file2species_map(infile):
    genome2species = {}
    with open(infile) as f:
        for line in f:
            genome, species = line.strip().split("\t")
            assert genome not in genome2species
            genome2species[genome] = species
    return genome2species


def fix_sylph_columns(infile, sample, run, file2species_map):
    with open(infile) as f:
        results = [x.rstrip().split("\t") for x in f]

    if len(results) == 0:
        logging.info("No sylph results")
        return

    genome2species = load_file2species_map(file2species_map)
    assert results[0][0] == "Sample_file"
    with open(infile, "w") as f:
        print("Sample", "Run", *results[0][1:], "Species", sep="\t", file=f)
        for l in results[1:]:
            genome_file = l[1].split("/")[-1]
            assert genome_file.endswith("_genomic.fna.gz") or genome_file.endswith(
                "_genomic.fna"
            )
            genome_file = genome_file.replace("_genomic", "")
            if genome_file.endswith(".fna"):
                genome_file += ".gz"
            print(sample, run, *l[1:], genome2species[genome_file], sep="\t", file=f)


def run_sylph(reads1, reads2, db, outfile):
    tmp_out = f"{outfile}.tmp.sketch"
    command = ["sylph", "sketch", "-1", reads1, "-2", reads2, "-d", tmp_out]
    logging.info("run: " + " ".join(command))
    try:
        subprocess.check_output(command)
    except:
        raise Exception("Error running sylph sketch: " + " ".join(command))

    command = f"sylph profile -t 1 {db} {tmp_out}/*.sylsp > {outfile}"
    logging.info("run: " + command)
    try:
        subprocess.check_output(command, shell=True)
    except:
        raise Exception(f"Error running sylph profile: {command}")

    try:
        subprocess.check_output(["rm", "-r", tmp_out])
    except:
        raise Exception(f"Error deleting temp sylph dir {tmp_out}")


def run_shovill(reads1, reads2, singularity_img, outdir):
    command = [
        "singularity",
        "exec",
        singularity_img,
        "shovill",
        "--R1",
        reads1,
        "--R2",
        reads2,
        "--cpus",
        "1",
        "--outdir",
        outdir,
    ]
    logging.info("run: " + " ".join(command))
    try:
        subprocess.check_output(command)
    except:
        raise Exception("Error running shovill: " + " ".join(command))

    contigs_fa = os.path.join(outdir, "contigs.fa")
    if not os.path.exists(contigs_fa):
        raise Exception(f"No contigs file found from shovill: {contigs_fa}")

    return contigs_fa


def parse_shovill_contigs(shovill_fa, out_fa, ctg_prefix, min_ctg_len):
    seq_reader = pyfastaq.sequences.file_reader(shovill_fa)
    with open(out_fa, "w") as f:
        for seq in seq_reader:
            if len(seq) < min_ctg_len:
                continue
            seq.id = ctg_prefix + seq.id
            print(seq, file=f)


def run_human_nucmer(asm_fa, ref_dir, outdir, nucmer_splitter_script):
    command = [nucmer_splitter_script, ref_dir, asm_fa, outdir]
    logging.info("run: " + " ".join(command))
    try:
        subprocess.check_output(command)
    except:
        raise Exception("Error running nucmer: " + " ".join(command))


def get_contam_contigs_from_nucmer_file(nucmer_file, min_pc_id=99, min_len_frac=0.9):
    contam_contigs = set()

    for d in csv.DictReader(open(nucmer_file), delimiter="\t"):
        if float(d["[% IDY]"]) < min_pc_id:
            continue

        if int(d["[LEN 2]"]) / int(d["[LEN Q]"]) < min_len_frac:
            continue

        contam_contigs.add(d["[NAME Q]"])

    return contam_contigs


def decontam(fasta_in, fasta_out, nucmer_file, min_pc_id=99, min_len_frac=0.9):
    to_remove = get_contam_contigs_from_nucmer_file(
        nucmer_file, min_pc_id=min_pc_id, min_len_frac=min_len_frac
    )
    logging.info(f"Number of contaminated contigs: {len(to_remove)}")
    reader = pyfastaq.sequences.file_reader(fasta_in)
    kept_contigs = 0
    with gzip.open(fasta_out, "wt") as f:
        for seq in reader:
            if seq.id.split()[0] not in to_remove:
                print(seq, file=f)
                kept_contigs += 1
    return kept_contigs


parser = argparse.ArgumentParser(
    description="Download reads, run sylph, run shovill, run human decontam, clean up files",
    usage="%(prog)s [options]",
)
parser.add_argument("--test1", help="For testing. reads file 1")
parser.add_argument("--test2", help="For testing. reads file 2")
parser.add_argument(
    "--min_ctg_len",
    type=int,
    help="Minimum contig length to keep from shovill [%(default)s]",
    default=200,
)
parser.add_argument("--syldb", required=True, help="Sylph db file")
parser.add_argument(
    "--shov_img", required=True, help="Singularity image file for shovill"
)
parser.add_argument(
    "--nuc_dir", required=True, help="Directory of nucmer reference files"
)
parser.add_argument(
    "--nuc_script", required=True, help="Full path to nucmer_splitter.py"
)
parser.add_argument(
    "--file2species", required=True, help="Full path to file2species_map file"
)
parser.add_argument("--run", required=True, help="Run accession")
parser.add_argument("--sample", required=True, help="Sample accession")
parser.add_argument(
    "--out", required=True, help="Output directory (must not already exist)"
)

options = parser.parse_args()
options.syldb = os.path.abspath(options.syldb)
options.shov_img = os.path.abspath(options.shov_img)
options.nuc_script = os.path.abspath(options.nuc_script)
options.file2species = os.path.abspath(options.file2species)

logging.basicConfig(
    format="[%(asctime)s process_one_sample  %(levelname)s] %(message)s",
    datefmt="%Y-%m-%dT%H:%M:%S%z",
)
log = logging.getLogger()
log.setLevel(logging.INFO)


os.mkdir(options.out)
os.chdir(options.out)

status_file = "status.txt"
set_status(status_file, "start")

logging.info("=============== GET READS ====================")
try:
    if options.test1 is not None and options.test2 is not None:
        fq1, fq2 = options.test1, options.test2
    else:
        dl_ok = False
        for i in range(1, 6):
            logging.info(f"Download reads attempt number {i} of 5")
            try:
                fq1, fq2 = download_reads(options.run)
            except:
                subprocess.check_output(["rm", "-rf", options.run])
                logging.info(f"Download reads attempt number {i} of 5 failed")
                time.sleep(random.randint(10, 30))
                continue
            dl_ok = True
            break
        if not dl_ok:
            raise Exception("5 attempts at downloading reads failed")
except:
    set_status(status_file, "downloaded_reads_fail")
    raise Exception("Error downloading reads. Stopping")
set_status(status_file, "downloaded_reads")


logging.info("========= CHECK READS FASTQ GZIP OK ==========")
fq1_gzip_ok = gzip_check(fq1)
fq2_gzip_ok = gzip_check(fq2)
if not (fq1_gzip_ok and fq2_gzip_ok):
    set_status(status_file, "reads_fastq_gzip_check_fail")
    raise Exception("Reads FASTQ file(s) failed gzip test. Stopping")
set_status(status_file, "reads_fastq_gzip_check")


logging.info("=============== SYLPH ========================")
sylph_file = "sylph.tsv"
try:
    run_sylph(fq1, fq2, options.syldb, sylph_file)
except:
    set_status(status_file, "sylph_fail")
    raise Exception("Error running sylph. Stopping")
set_status(status_file, "sylph")

try:
    fix_sylph_columns(sylph_file, options.sample, options.run, options.file2species)
except:
    set_status(status_file, "sylph_fix_columns_fail")
    raise Exception("Error fixing sylph output file. Stopping")
set_status(status_file, "sylph_fix_columns")


logging.info("=============== SHOVILL ======================")
shovill_dir = "shovill"
try:
    shovill_fa = run_shovill(fq1, fq2, options.shov_img, shovill_dir)
except:
    set_status(status_file, "shovill_fail")
    raise Exception("Error running shovill. Stopping")
set_status(status_file, "shovill")


logging.info("=============== RENAME CONTIGS ===============")
shovill_rename_fa = "contigs.length_filtered.fa"
try:
    parse_shovill_contigs(
        shovill_fa, shovill_rename_fa, f"{options.sample}.", options.min_ctg_len
    )
except:
    set_status(status_file, "shovill_parse_fail")
    raise Exception("Error parsing shovill contigs. Stopping")

logging.info("=============== NUCMER =======================")
nucmer_dir = "nucmer_human"
try:
    run_human_nucmer(shovill_rename_fa, options.nuc_dir, nucmer_dir, options.nuc_script)
except:
    set_status(status_file, "nucmer_fail")
    raise Exception("Error running nucmer. Stopping")
set_status(status_file, "nucmer")


logging.info("=============== DECONTAMINATE ================")
final_fasta = f"{options.sample}.fa.gz"
nucmer_file = os.path.join(nucmer_dir, "nucmer.coords")
try:
    number_contigs_kept = decontam(shovill_rename_fa, final_fasta, nucmer_file)
except:
    set_status(status_file, "decontam_fail")
    raise Exception("Error decontaminating. Stopping")
set_status(status_file, "decontam")
logging.info(
    f"Number of contigs remaining after decontamination: {number_contigs_kept}"
)

logging.info("=============== CLEAN UP =====================")
subprocess.check_output(f"gzip -c -9 {nucmer_file} > nucmer_human.gz", shell=True)
subprocess.check_output(["rm", "-r", options.run])
subprocess.check_output(["rm", "-r", shovill_dir])
subprocess.check_output(["rm", "-r", nucmer_dir])
os.unlink(shovill_rename_fa)


set_status(status_file, "finished")
logging.info("=============== FINISHED =====================")
