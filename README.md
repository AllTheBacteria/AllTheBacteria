# AllTheBacteria
Follow up to Grace Blackwell's 661k dataset, for 2023.
Could really do with a better project (and repo) name. CurrentBacterialGenomes2023?

## Release 0.1
First release will contain
1. Unique identifier for each assembly, with a 1:1 mapping with ENA/SRA run ids.
2. About 2 million Shovill assemblies, one for each identifier above. (Any contig aligning to human T2T or mouse is removed)
3. File(s) summarising taxonomic and contamination statistics based on mapping reads to human, mouse, and Kraken/Bracken of reads with a GTDB database; CheckM2 etc.
4. A filelist specifying an initial suggested list of "high quality" assemblies (ie a subset of the 2 million, based on the QC stats)
5. A README decribing all this, plus pointing to a Github with links to how all of the above was done, plus explaining rules of engagement (see below)

Timeline - will aim for November 2023. Assemblies are done, just QC left.

## Further releases
Future releases will include
1. Annotation (bakta at least)
2. Pan-genomes and harmonised gene names within species (for the top N species) for representative genomes chosen using poppunk clusters and QC metrics.
3. MLST, various species specific typing, AMR
4. Search indexes (COBS, pp-sketchlib, sourmash, others?)
No timeline on these yet - see project management below.

## Distribution
Data will be distributed at least by
1. EBI Globus endpoint
2. Zenodo, so we can have a data doi. Zipped, the assemblies should only be ~100Gb.
Will look into AWS

## Rules of Engagement with the data
Once Release 0.1 is out, anyone/everyone is welcome to use the data and publish with it. There is no expectation that the people who made the release/data should be co-authors on these publications, but we would appreciate citation of the data doi. Once we manage to write a paper about this, we ask that anyone using the data, cites the paper. 

## Rules of Involvement with the project
All welcome, contact us via Github, Slack or the monthly zoom calls. Anyone who contributes to the project, through analysis, project management or any other means, ought to be an author of the paper. 

## Project Management
1. In terms of tracking, this will be done via Github. @happykhan has volunteered to sort out kanban integration in github (not via zenhub i believe, but something else)
2. I propose we have monthly zoom calls to keep in touch with updates from each person who has taken on a work package, default length of a call should be 15 mins unless we have something to say. I'd suggest we start them after Release 0.1, but there are a number of people who have kindly volunteered to take on work, and if anyone wants to start sooner, that's fine with me.

## FAQ
1. What happens if two people want to run their competing methods (bad example, prokka versus bakta or one AMR tool versus another). First, anyone can do anything they like, but to get into the releases, we should discuss on a zoom call and make a decision. I propose we tend towards allowing multiple analyses (eg I intend to run bakta on everything but if someone wants to run prokka too, we should we ok to add that to the release too). However, if it starts to get silly with people wanting 4 tools each run with 3 parameters, then I think we get a lot stricter - this compute isn't free (in terms of carbon, or money), so we'll make a decision and do something limited. 

