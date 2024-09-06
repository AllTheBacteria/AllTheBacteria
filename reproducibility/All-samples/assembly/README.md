# Assembly pipeline

The first (up to release 0.2) AllTheBacteria assemblies were made using
https://github.com/leoisl/bacterial_assembly_pipeline
and then separately post-processed for human decontamination.

This page describes assemblies after release 0.2.
At the time of writing, this has been used to make the incremental
release 2024-08.

## Overview

There is a single script `process_one_sample.py`, which processes one
sample/paired Illumina run. The input is the run and sample accession, plus
required singularity containers and data files (these files are all publicly
available - see below). The script:
1. Downloads the reads using `enaDataGet` from [enaBrowserTools](https://github.com/enasequence/enaBrowserTools).
   It tries 5 times then gives up.
2. Runs [sylph](https://github.com/bluenote-1577/sylph) on the reads, for
   speciation
3. Assembles using [shovill](https://github.com/tseemann/shovill).
   Removes contigs shorter than 200bp.
4. Runs `nucmer` (from [MUMmer](https://github.com/mummer4/mummer)) against
   the human genome plus HLA sequences. Contigs that have a match with at least
   99% identity and 90% of their length are removed.
5. Deletes all intermediate files.



## Requirements

To use the script `process_one_sample.py`, you will need these installed:
* `enaDataGet` from  [enaBrowserTools](https://github.com/enasequence/enaBrowserTools)
* The python package `pyfastaq` (`pip install pyfastaq`)
* [Singularity](https://github.com/sylabs/singularity)
* [sylph](https://github.com/bluenote-1577/sylph)
* [MUMmer](https://github.com/mummer4/mummer) (specifically `nucmer`,
  `delta-filter` and `show-coords`)

You will also need these input files. Commands to download them are below.
* Sylph database file
* A lookup file so sylph can get GTDB species names.
  It was made with the script `make_gtdb_syldb_file2species_map.sh`.
* A shovill singularity image file. We made it with
  `singularity build shovill.1.1.0-2022Dec.img docker://staphb/shovill:1.1.0-2022Dec`
* The nucmer wrapper script [`nucmer_splitter.py`](https://github.com/martinghunt/bioinf-scripts/blob/master/python/nucmer_splitter.py)
* A directory of nucmer human/HLA reference files. It was made
  with the script `make_nucmer_ref.sh`.

Here are example wget commands to download all the latest files at
the time of writing:
```
wget https://storage.googleapis.com/sylph-stuff/v0.3-c200-gtdb-r214.syldb
wget -O gtdb_r214.syldb.file2species.map https://osf.io/download/3427r/
wget -O shovill.1.1.0-2022Dec.img https://osf.io/download/66b4d22a9669267870932e76/
wget https://raw.githubusercontent.com/martinghunt/bioinf-scripts/master/python/nucmer_splitter.py
chmod 755 nucmer_splitter.py
wget -O GCA_009914755.split_ref.tar.xz https://osf.io/download/66b5d0ea8e31d3ee729b4217/
tar xf GCA_009914755.split_ref.tar.xz
```

## How to run

The usage is like this (filenames match the previous download commands):
```
process_one_sample.py \
    --run <RUN ACCESSION> \
    --sample <SAMPLE ACCCESSION> \
    --out <OUTPUT DIRECTORY> \
    --syldb /path/to/v0.3-c200-gtdb-r214.syldb \
    --file2species /path/to/gtdb_r214.syldb.file2species.map \
    --shov_img /path/to/shovill.1.1.0-2022Dec.img \
    --nuc_script /path/to/nucmer_splitter.py \
    --nuc_dir /path/to/GCA_009914755.split_ref
```

It will take up to around 17GB of RAM, and take anything from about 1 hour
to several hours to run, depending on the sample.

## Output files

* `status.txt` - summary of what stage it got to. "Finished" means everything
 ran ok.
* `<SAMPLE ACCESSION>.fa.gz` - assembly in FASTA format. This is the assembly
  made by shovill, but with contigs matching human/HLA removed. The sample
  accession is added to each contig name.
* `sylph.tsv` - sylph output
* `nucmer_human.gz` - nucmer output of contigs compared to human genome/HLA
  sequences.


## Notes on EBI SLURM cluster

The script was run on the EBI SLURM cluster using job arrays.
For reproducibility, the helper scripts are included here, and a description
of how everything was run. It assumes you are familiar with SLURM and job arrays.

First, make a tab-delimited file of sample and run accessions to be processed.
One sample per line, column1=sample, column2=run. No header line. eg:
```
SAMN42497439	SRR29831084
SAMN42497440	SRR29831335
SAMN42497441	SRR29831663
SAMN42497442	SRR2983109
```

Make a directory for logs, and for the assembly output directories:
```
mkdir -p /FIX_PATH/logs
mkdir -p /FIX_PATH/assemblies
```

Each element of the job array runs the bash script `run_one_sample.sh` - this
is a wrapper around `process_one_sample.py`.
It gets the job array index, gets the corresponding line number from the
file of sample/run accessions, and processes that sample.

You will need to edit the paths in `run_one_sample.sh` to point to the
correct places - everywhere where there is `FIX_PATH`.

The job array was run using the script `slurm_array.sbatch`. You will also
need to edit the paths in there to point to the correct places. In particular,
edit these lines:
```
#SBATCH --output=/FIX_PATH/logs/%a.o
#SBATCH --error=/FIX_PATH/logs/%a.e
```
to match the logs directory you made earlier. The size of the job array should
be the same as the number of samples, which is the number of lines in the
file of sample/run accessions. Edit this line accordingly:
```
#SBATCH --array=1-1000%100
```
The paths in this line:
```
./run_one_sample.sh /FIX_PATH/assemblies /FIX_PATH/sample_and_runs_file
```
should match the assemblies directory made earlier, and the samples/run
accessions file.

Job array element `N` will write stdout to `/path/to/logs/N.o`, stderr to
`/path/to/logs/N.e`, and output of `process_one_sample.py`
to `/path/to/assemblies/<SAMPLE_ACCESSION>/`.


It's not uncommon for downloads to fail. Repeatedly. More than the 5 times
attempted by the pipeline. You can clean out all the files from failed
downloads with this:
```
clean_failed_downloads.py sample_and_runs_file /FIX_PATH/assemblies /FIX_PATH/logs
```
It will find all the samples where the reads download failed, delete their
assembly output directories and `.o` and `.e` files, and print
a comma-separated list of the array indexes, so they can then be easily
rerun by pasting that list into the `#SBATCH --array=...` line of the sbatch
script.


Finally, make a summary of the job array with:
```
array_summary.py sample_and_runs_file \
  /FIX_PATH/assemblies \
  /FIX_PATH/logs \
  out
```
It makes these files:
* `out.status.gz` - the overall status of each sample. Most will say
  "finished", meaning everything was ok. Otherwise it is the reason for
  failing.
* `out.logs.gz` - all of the `.e` files (which have logging output) catted,
  but with the sample accession added to the start of each line
* `out.sylph.tsv.gz` - sylph results
* `out.sylph.no_matches.txt.gz` - list of samples with no sylph output
* `out.nucmer.gz` - nucmer output files catted (each contig has the
  sample accession in its name).

Some notes:
* The time limit for each job was set to 1000 minutes. Some samples did hit this
  time limit. Their status was replaced with "timeout". If a sample hits this
  limit, we probably don't want it (metagenomics? contamination?) and so
  was not rerun with a longer time limit.
* Some FASTQ files were found to be invalid (running `gzip --test` on them
  outputs "unexpected end of file"), even though the MD5 was ok. Then sylph
  tries to use them and throws errors. These samples have a status of
  `sylph_fail` because that is the stage that crashed. Sorry sylph, we know
  it's not really your error.

