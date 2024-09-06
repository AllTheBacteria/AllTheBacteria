Overview
========

Where are the data?
-------------------

There are three places to go, depending on what you want:

1. How to download and use the data/analysis files is described in this
   documentation you are currently reading
2. The data are all hosted here on OSF: https://osf.io/xv7q9/
   - this includes assembly and analysis files
3. In-depth methods details and files for reproducibility are stored in this
   github repository: https://github.com/AllTheBacteria/AllTheBacteria.
   If you are just using the data, you shouldn't need to look there.

If you only want to use the data without caring about the methods then
we suggest you read this documentation, which has the relevant links to OSF,
as opposed to going directly to OSF.


A brief history of AllTheBacteria
---------------------------------

Original data
~~~~~~~~~~~~~

AllTheBacteria is a follow up to Grace Blackwell's 661k dataset, which
covered everything up to November 2018: https://doi.org/10.1371/journal.pbio.3001421.


Releases 0.1 and 0.2
~~~~~~~~~~~~~~~~~~~~

In March 2024 we released version 0.1 of AllTheBacteria, which added
1,271,428 new assemblies to the 661k dataset, taking the total to
1,932,812 assemblies. It included all data up to May 2023.
This is described in the bioRxiv preprint: https://doi.org/10.1101/2024.03.08.584059.
The files were put on the EBI ftp site (https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/).

We found 11,887 assemblies containing  some contigs had matched the human
genome. We removed these contigs, calling the resulting assemblies
release 0.2. The original 0.1 release was deleted from the EBI
ftp site, so that now only release 0.2 is available. Releases 0.1 and 0.2
contain the same samples, the only difference is 11,887 assemblies
had one or more contigs removed.


Species names and migration from EBI ftp to OSF
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The assembly files are compressed using miniphy, which (approximately)
batches files by species names. These species names are used in the output
files. However, species calling will never be perfect, and so we wanted
to remove species names from the assembly files.

We decided to host the data at OSF from release 0.2 onwards. All files
on the EBI ftp site are left as an archive. Those files do have species
names in them. The files were renamed before uploading to OSF. The
assemblies are identical in release 0.2 on from EBI and OSF, but
the filenames are different.


Update in August 2024
~~~~~~~~~~~~~~~~~~~~~

After release 0.2, we processed all new data up to August 2024,
and released these new 507,566 assemblies with the name "incremental release
2024-08". It is called "incremental" because it only contains the new
assemblies. This means that the complete AllTheBacteria dataset is
release 0.2 plus incremental release 2024-08.

