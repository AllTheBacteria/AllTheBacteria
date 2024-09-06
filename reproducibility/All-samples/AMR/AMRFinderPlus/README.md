# AMRFinderPlus

Version AMRFinderPlus used: 3.12.8.

Version AMRFinderPlus database used: 2024-01-31.1.

The workflow was run on the EBI SLURM cluster.

AMRFinderPlus was run in 10000 batches with each batch created by the `split_into_batches` checkpoint.

## Inputs

* `sample_list`: A newline delimited files of sample IDs to run on.
* `path_file`: A tsv file with the sample ID in the first column and the path to the assembly the second column.
* `species_file`: A tsv file with the sample ID in the first column and the GTDB species call of each sample in the second column.

## Species calls

`GTDB_AMRFP_mapping` is a dictionary mapping the GTDB species name to the AMRFinderPlus `--organism`. If there is no AMRFinderPlus organism available to match to the GTDB species for a particular sample then this option was not used when running AMRFinderPlus.

## Final output

All AMRFinderPlus results, files of failed runs and files of empty runs were joined together ad-hoc and a status file created to indicate if AMRFinderplus finished successfully ("PASS"), failed ("FAILED") or is yet to be run ("NOT DONE").