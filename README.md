# AllTheBacteria
All WGS isolate bacterial INSDC data to June 2023uniformly assembled, QC-ed, annotated, searchable.

Follow up to Grace Blackwell's 661k dataset (which covered everything to Nov 2018).

Preprint: https://doi.org/10.1101/2024.03.08.584059

## Documentation

Please see: https://allthebacteria.readthedocs.io/en/latest/

## Latest Release 0.2
The data are here: https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/

Changes from release 0.1 are documented in detail in the release 0.2 readme: https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/README.md

Summary of changes:
* Approximately 12k contigs were removed, due to matching the human genome
* Reran assembly stats and checkm2 on the changed assemblies
* The "high quality" dataset changed slightly because of the assemblies changing
* Species call for each sample tidied up
* Added phylign indexes for searching/aligning query sequences (see https://github.com/AllTheBacteria/Phylign/blob/main/README.md)
* Updated sketchlib indexes
* Added file of md5sum of all files in the release


## Release 0.1
Full details here: https://www.biorxiv.org/content/10.1101/2024.03.08.584059v1
The data were here: https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.1/
but have been deleted due to human contamination. Please use release 0.2 instead.

First release contains
1. About 2 million Shovill assemblies, identified by ENA sample id
2. summary of assembly statistics
3. File(s) summarising taxonomic and contamination statistics based on sylph taxnonomic abundance estimation (GTDB r214), and CheckM2
4. A filelist specifying  "high quality" assemblies
5. A README decribing all this.
The assembly workflow is in github , but we don't have a distributable container for it yet.

## Further releases
Future releases will include
1. More search indexes to come.
2. Annotation (bakta at least)
3. Pan-genomes and harmonised gene names within species (for the top N species) for representative genomes chosen using poppunk clusters and QC metrics.
4. MLST, various species specific typing, AMR


## Distribution
Data will be distributed at least by
1. EBI ftp which is simutaneously accessible by Globus and Aspera.
2. Zenodo would be good to add


## Rules of Engagement with the data
Once Release 0.1 is out, anyone/everyone is welcome to use the data and publish with it. There is no expectation that the people who made the release/data should be co-authors on these publications, but we would appreciate citation of the preprint (https://www.biorxiv.org/content/10.1101/2024.03.08.584059v1).

## Rules of Involvement with the project
All welcome, contact us via Github, Slack or the monthly zoom calls. Anyone who contributes to the project, through analysis, project management or any other means, ought to be an author of the paper.

## Next zoom calls
22nd March 2024, 9am and 4pm GMT



## FAQ
1. What happens if two people want to run their competing methods (bad example, prokka versus bakta or one AMR tool versus another). First, anyone can do anything they like, but to get into the releases, we should discuss on a zoom call and make a decision. We shall tend towards allowing multiple analyses (eg we intend to run bakta on everything but if someone wants to run prokka too, we should we ok to add that to the release too). However, if it starts to get silly with people wanting 4 tools each run with 3 parameters, then I think we get a lot stricter - this compute isn't free (in terms of carbon, or money), so we'll make a decision and do something limited.

