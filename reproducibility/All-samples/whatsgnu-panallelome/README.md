# WhatsGNU Allele Frequency Analysis for AllTheBacteria

## Overview

[WhatsGNU](https://github.com/ahmedmagds/WhatsGNU) computes protein allele frequencies across bacterial genomes. This analysis builds a comprehensive WhatsGNU database from the AllTheBacteria Bakta protein annotations (`.faa` files), covering 2,438,285 genomes across release 0.2 and incremental release 2024-08.

The database enables users to query any bacterial genome and obtain, for each of its proteins, the number of exact matches (GNU score) across all 2.4M+ genomes, along with the species distribution of those matches.

**Custom implementation note:** This analysis uses a custom reimplementation of WhatsGNU (`WhatsGNU_ATB_DB.py`) optimised for the scale of AllTheBacteria. It uses LMDB-backed sharded storage (8 shards) with numpy for hashing. The query tool (`Query_WhatsGNU_ATB.py`) is also custom-built for this database format. Both scripts are included in this directory.

## Genome coverage

| Category | Count |
|---|---|
| Total in AllTheBacteria | 2,440,377 |
| PASS (`.faa` file present, included in DB) | 2,438,285 |
| FAIL — `bakta_io` parse error (incomplete JSON) | 2 |
| FAIL — missing from Bakta status file | 1 |
| NOT_DONE — unavailable (NA in all Bakta status categories) | 2,089 |

Failed samples:
- `SAMN05250556` — incomplete `bakta.json` in `atb.bakta.r0.2.batch.472.tar.xz` (md5 matches status file, so not a download/extraction issue)
- `SAMN03257089` — incomplete `bakta.json` in `atb.bakta.r0.2.batch.646_d.tar.xz`
- `SAMN38787634` — missing from Bakta status file entirely but present in `species_calls_aggregated.tsv`

The accessions for the 2092 genomes that failed the bakta_io JSON->FAA conversion can be found on OSF Genomes_2092_failed_bakta_io_conversion.txt. The accessions for the genomes that were included in the WGNU_ATB_DB is available on OSF in this file final_2438285_genomes.txt.

## Software and dependencies

| Software | Version | Notes |
|---|---|---|
| Python | 3.x (conda-forge) | via `conda create -n WGNU_ATB conda-forge::python` |
| numpy | (pip) | Core hashing library |
| lmdb | (pip) | Sharded key-value database backend |
| pandas | (pip) | Sample table handling |
| matplotlib | (pip) | Plotting (allelome figures) |
| networkx | (pip) | Plotting dependencies |
| adjustText | (pip) | Plotting label placement |
| seaborn | (pip) | Plotting |
| Bakta | (conda, bioconda) | Upstream annotation (ATB Bakta JSON annotations used as input) |

## Workflow

The full pipeline has six stages. All commands below were run on a SLURM-managed HPC cluster. Paths are specific to our environment and would need to be adapted.

### Stage 1 — Download Bakta annotation archives from OSF

Bakta annotation archives (`.tar.xz`) were downloaded from the AllTheBacteria OSF project using a SLURM array job:

```bash
conda activate bakta

# Download in parallel via SLURM array (942 archive batches, 120 concurrent)
sbatch --array=1-942%120 atb_download_one.sbatch
```

### Stage 2 — Extract protein FASTA files from Bakta JSON archives

The Bakta `.tar.xz` archives contain `.bakta.json` files. We extracted `.faa` (protein FASTA) files using `bakta_io` (`json_io.py`), which outputs only `.faa` files.

```bash
TSV=atb.tsv
SCR_ROOT=/scr1/users/$USER/ATB/atb_bakta_convert
mkdir -p "$SCR_ROOT"/{chunks,args,logs,tasks}

# Build a sorted, deduplicated jobs file from the download manifest
awk -F $'\t' '
NR==1{
  for(i=1;i<=NF;i++) h[$i]=i
  next
}
{
  print $h["filename"] "\t" $h["url"] "\t" tolower($h["md5"])
}
' "$TSV" | sort -u > "$SCR_ROOT/jobs.tsv"

# Split into chunks of 10 archives each
split -l 10 -d -a 5 "$SCR_ROOT/jobs.tsv" "$SCR_ROOT/chunks/chunk_"
ls -1 "$SCR_ROOT"/chunks/chunk_* | sort > "$SCR_ROOT/args/args_chunks"

# Run conversion via SLURM array (95 chunk jobs, 50 concurrent). This will use atb_bakta_pipeline_v2.py.
sbatch --array=1-95%50 sbatch_atb_bakta_convert_array.sh

# Final count verification
ls -1 faa/ > final_2438285_genomes.txt
wc -l final_2438285_genomes.txt
# Expected: 2438285
```

### Stage 3 — Assign integer IDs by species

Each genome was assigned a stable integer ID, grouped by species, for use as compact identifiers in the LMDB database:

```bash
python assign_ids_by_species.py \
    --in species_calls_aggregated.tsv \
    --out_dir species_samples_hashing_final \
    --include_samples final_2438285_genomes.txt
```

This produces `samples_with_ids.tsv`, which maps each SAM* accession to an integer ID and species name to an id. It will also produce species_stats.tsv

### Stage 4 — Build WhatsGNU LMDB database

The core database build uses `WhatsGNU_ATB_DB.py`, which hashes each protein sequence (MD5), counts exact matches across all genomes, and stores counts and posting lists in 8 LMDB shards:

```bash
conda activate WGNU_ATB

# Submitted via SLURM (see sbatch_WhatsGNU_ATB_3.sh for resource requests)
sbatch sbatch_WhatsGNU_ATB_DB.sh
```

The sbatch script runs:

```bash
python WhatsGNU_ATB_DB.py \
    --sample_table samples_with_ids.tsv \
    --faa_dir faa/ \
    --out_dir WGNU_ATB_DB/ \
    --tmp_dir /scr1/users/$USER/WGNU_tmp_$SLURM_JOB_ID \
    --shards 8 \
    --with_postings \
    --sort_mem_mb 13107 \
    --lmdb_map_gb_counts_per_shard 12 \
    --lmdb_map_gb_postings_per_shard 80 \
    --log_file build.log \
    --log_level INFO
```

### Stage 5 — Build hash-to-sequence lookup table

For users who want to retrieve the actual amino acid sequence for a given allele hash:

```bash
sbatch submit_hash_table.sbatch
#This sbatch script uses build_hash_sequence_table_v4.py for making a table of hash->sequence and count number of faa records in each file (records_per_faa.tsv) and for each species (records_per_species.tsv).
```

### Stage 6 — Generate allelome diversity plots

Publication-quality figures summarising allelic diversity across species:

```bash
# Build cache of per-species allele statistics and generate figures and tables
sbatch bash_allelome_plots.sh
# Runs: build_allelome_cache.py and allelome_plots_v5.py 

# Generate final publication figures and summaries
sbatch submit_figures_v3.sbatch
# Runs: allelome_publication_plots_v2.py
```

Output includes:
- Publication-quality PDF/PNG figures and Summary Tables

## Querying the database

To query a genome against the pre-built database, use the [Query_WhatsGNU_ATB.py](https://github.com/microbialARC/WhatsGNU-ATB/blob/main/Query_WhatsGNU_ATB.py):

```bash
./Query_WhatsGNU_ATB.py \
    --db_dir WGNU_ATB_DB/ \
    --shards 8 \
    --faa your_genome.bakta.faa \
    --include_sequence \
    --samples_tsv samples_with_ids.tsv \
    --species_names_tsv samples_with_ids.tsv \
    --with_postings \
    --out_dir query_results/
```

See the [readthedocs documentation](https://allthebacteria.readthedocs.io/en/latest/whatsgnu-panallelome.html) for user-facing instructions on downloading and querying the database.

## Scripts in this directory

| Script | Purpose |
|---|---|
| `atb_download_one.sbatch` | SLURM array job for downloading Bakta archives |
| `sbatch_atb_bakta_convert_array.sh` | SLURM array job for JSON → FAA conversion |
| `atb_bakta_pipeline_v2.py` | converts JSON to FAA |
| `assign_ids_by_species.py` | Assign stable integer IDs grouped by species |
| `sbatch_WhatsGNU_ATB_DB.sh` | SLURM submission script for database build |
| `submit_hash_table.sbatch` | SLURM submission script for Hash-to-sequence table |
| `build_hash_sequence_table_v4.py` | Hash-to-sequence lookup table builder |
| `bash_allelome_plots.sh` | SLURM submission script for allelome cache and plots |
| `build_allelome_cache.py` | One-time cache builder for ATB WhatsGNU allelome DB |
| `allelome_plots_v5.py` | ATB WhatsGNU allelome summary plot analysis |
| `submit_figures_v3.sbatch` | SLURM submission script for publication figures |
| `allelome_publication_plots_v2.py` | Publication figure generation |


## WhatsGNU ATB DB-builder and Query Scripts available from [WhatsGNU-ATB GitHub Repository](https://github.com/microbialARC/WhatsGNU-ATB)

| Script | Purpose |
|---|---|
| `WhatsGNU_ATB_DB.py` | Core ATB database builder (LMDB + numpy hashing) |
| `Query_WhatsGNU_ATB.py` | Query tool for searching genomes against the ATB database |


## OSF File Summary

**OSF project:** [https://osf.io/6jr4u/](https://osf.io/6jr4u/)

| Folder / File | Description |
|---|---|
| **WGNU_ATB_DB/** | Pre-built WhatsGNU database for querying. Required for `Query_WhatsGNU_ATB.py`. Contains 8 LMDB count shards (`lmdb_counts/shard_00` – `shard_07`), 8 LMDB posting shards (`lmdb_postings/shard_00` – `shard_07`), a binary genome-to-species index (`indexes/genome_species.u32`), a function lookup table (`metadata/functions.tsv.gz`), Mapping file for each SAM* accession to an integer SampleID and SpeciesID (`samples_with_ids.tsv`), build parameters and statistics (`metadata/build_info.json`), and the build log (`build.log`). Each shard directory contains `data.mdb` and `lock.mdb`. You will need to download the entire folder to use with the Query script |
| **Sample_tables/** | Reference files mapping genomes to IDs, species, and summary statistics. |
| ↳ `final_2438285_genomes.txt` | List of all 2,438,285 genome accessions included in the database. |
| ↳ `Genomes_2092_failed_bakta_io_conversion.txt` | List of all 2,092 genomes that failed the bakta_io step and were not included. |
| ↳ `species_stats.tsv` | Summary statistics per species (genome counts including counts for high quality genomes). |
| ↳ `records_per_faa.tsv` | Number of proteins per genome (FAA file). |
| ↳ `records_per_species.tsv` | Number of proteins per species before exact match compression. |
| **ATB_hash_seq/** | Hash-to-sequence lookup table, split into 20 xz-compressed parts (`hash_to_sequence_part_00.xz` – `part_19.xz`). Each row maps a 128-bit BLAKE2b allele hash to its amino acid sequence. Reassemble with `cat hash_to_sequence_part_*.xz | xz -d > hash_to_sequence.tsv`. |
| **ATB_summary_figures_tables/** | Results from the allelome diversity analysis across all species. |
| ↳ `tables/` | TSV files including: global GNU score distributions (`01_global_gnu_hist_data.tsv`), per-species GNU histograms (`02_species_*_gnu_hist_data.tsv` for top 20 species), function frequency tables (`02_functions_*.tsv`), species coverage estimates (`03_species_coverage_*.tsv`), species-sharing network edges and nodes (`05_species_*.tsv`), top species pairs by shared alleles (`06_top10_species_pairs.tsv`), GNU distribution summaries and top/bottom alleles (`07_*.tsv`), unique vs shared allele breakdowns (`08_*.tsv`), function dominance analysis (`09_function_dominance.tsv`), cross-species allele tables (`NEW1–NEW5_*.tsv.gz`), and an all-species summary (`NEW5_all_species_summary.tsv`). |
| ↳ `figures/` | PNG plots corresponding to the tables above: global and per-species GNU histograms, function frequency bar charts, species coverage curves, species-sharing heatmaps, and unique vs shared allele comparisons. |
| ↳ `publication_figures/` | Publication-quality PNG figures (`pub_01` – `pub_08`): alleles vs genomes scaling, GNU distributions, coverage bars, shared-allele heatmaps, species network, protein vs allele counts, frequency class breakdowns, cumulative distributions, and protein distribution plots. |
| ↳ `cache/counts_cache.npz` | Pre-computed numpy cache of allele counts from the LMDB database. Used by the plotting scripts to avoid re-reading all shards. Can be regenerated from the database. |

## Cluster-specific notes

All jobs were run on a SLURM-managed HPC cluster at the Children's Hospital of Philadelphia. Paths such as `/mnt/isilon/allthebacteria/` and `/scr1/users/$USER` are specific to this environment. The sbatch scripts contain hard-coded resource requests and paths that would need to be adapted for other clusters. The scripts are provided for documentation and reproducibility purposes, not as a turnkey pipeline.

## Contact

Ahmed Moustafa — moustafaam@chop.edu
