GECCO version 0.9.8 - run as a container
Nextflow version 24.04.2 - loaded as module on the cluster
The nextflow workflow was run on the HPC2N cluster (Umeå).
For the incremental release (08/2024) the --merge-gbk option was added to the gecco command due to file limits on the cluster.
The genomes were run in batches, which were concatenated to the final results files.
Due to file size, the GenBank files were split into 2 files for the incremental release (08-2024) and 3 files for the v0.2 release.

The nextflow workflow is present in the file main.nf.
The associated configuration file is called nextflow.config (note that the executor is set to "slurm" in the available configuration file).
The command which was used to run the workflow: nextflow run main.nf -profile hpc
Upon failure of the workflow, the resume option (-resume) was added to the command above to resume the analysis.


path_to_genomes: the internal path to where the genomes are stored
path_to_container: the internal path to the GECCO v0.9.8 container
project_ID: ID associated with project allocation on the cluster
