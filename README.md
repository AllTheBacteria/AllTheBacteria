# AllTheBacteria
Follow up to Grace Blackwell's 661k dataset, for 2023.
Could really do with a better project (and repo) name. CurrentBacterialGenomes2023?

## Release 0.1
Full details here: https://www.biorxiv.org/content/10.1101/2024.03.08.584059v1
Data here: https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.1/
First release contains
1. About 2 million Shovill assemblies, identified by ENA sample id
2. summary of assembly statistics
3. File(s) summarising taxonomic and contamination statistics based on sylph taxnonomic abundance estimation (GTDB r214), and CheckM2 
4. A filelist specifying  "high quality" assemblies
5. A README decribing all this.
The assembly workflow is in github , but we don't have a distributable container for it yet.
   

## Further releases
Future releases will include
1. The process which is mapping all contigs against the human genome to id contamination is taking some time. We will have to make a new release
   which removes a small number of contigs from a small proportion of the genomes.
2. More search indexes to come.   
3. Annotation (bakta at least)
4. Pan-genomes and harmonised gene names within species (for the top N species) for representative genomes chosen using poppunk clusters and QC metrics.
5. MLST, various species specific typing, AMR


## Distribution
Data will be distributed at least by
1. EBI ftp which is simutaneously accessible by Globus and Aspera.
2. Zenodo would be good to add

   
## Rules of Engagement with the data
Once Release 0.1 is out, anyone/everyone is welcome to use the data and publish with it. There is no expectation that the people who made the release/data should be co-authors on these publications, but we would appreciate citation of the data doi. Once we manage to write a paper about this, we ask that anyone using the data, cites the paper. 

## Rules of Involvement with the project
All welcome, contact us via Github, Slack or the monthly zoom calls. Anyone who contributes to the project, through analysis, project management or any other means, ought to be an author of the paper. 

## Next zoom calls
22nd March 2024, 9am and 4pm GMT



## FAQ
1. What happens if two people want to run their competing methods (bad example, prokka versus bakta or one AMR tool versus another). First, anyone can do anything they like, but to get into the releases, we should discuss on a zoom call and make a decision. We shall tend towards allowing multiple analyses (eg we intend to run bakta on everything but if someone wants to run prokka too, we should we ok to add that to the release too). However, if it starts to get silly with people wanting 4 tools each run with 3 parameters, then I think we get a lot stricter - this compute isn't free (in terms of carbon, or money), so we'll make a decision and do something limited. 

