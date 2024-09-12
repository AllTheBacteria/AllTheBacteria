===============
Release History
===============

Release Version 0.1
===================

WE HAVE REMOVED RELEASE 0.1 assemblies and indexes,
as it contained human genome contamination;
please see release 0.2 instead, which documents precisely which contigs
were removed. Release 0.1 metadata is still available.

Release Version 0.2
===================

Summary
-------

This the second release from the AllTheBacteria project, which seeks to
make available a set of uniformly assembled and QC-ed genomes consisting
of all single-isolate WGS illumina samples from the ENA/SRA as of a fixed
date (in this case June 16th 2023). In future releases, through engagement with
various research communities, these assemblies will
be accompanied by gene annotation, pangenomes, feature annotation (eg
AMR genes, MLST, serotypes) and mobile element detection. Finally,
we will also release multiple different types of search index.
Release 0.2 provides the assembly, taxonomic information, basic
assembly quality information, and 2 types of search index. It is an updated
of version 0.1 that has human contamination removed from assemblies.

Please raise any issues here: https://github.com/iqbal-lab-org/AllTheBacteria

Citation: https://doi.org/10.1101/2024.03.08.584059


Changes from version 0.1 to version 0.2
---------------------------------------

Human decontamination:

* 11,887 assemblies had contigs removed because they matched the human genome.
* Added ``metadata/contam_contigs.json.gz``, which contains the samples and
  contig ids that were removed.
* No contigs were renamed. eg if contig 3 was removed from an assembly that had
  contigs 1-5, then the contigs in the new assembly are called 1,2,4,5
* Added ``metadata/nucmer_human.gz``, which has the raw nucmer output from
  mapping all assemblies to the human genome + HLA sequences

These were rerun on the assemblies that had human contamination contigs removed:

* assembly-stats, so the file ``metadata/assembly-stats.tsv.gz`` is updated
* checkm2, so the file ``metadata/checkm2.tsv.gz`` also updated

The high quality dataset has also changed slightly, because of the changed
assemblies:

* the script to generate a "high quality" dataset has been
  updated. It is now called ``metadata/make_hq_sample_list.py``, and has
  all cutoff exposed to the user, so it can be rerun with different
  parameters

Species calls:

* Version 0.1 had quick/hacky (not always correct) species calls made solely
  for compressing the assemblies (in ``metadata/ample2species2file.tsv.gz``).
  It also had more accurate species calls (in
  ``metadata/hq_dataset.species_calls.tsv.gz``) from more careful parsing of sylph
  results - these were used for the "high quality" dataset analysis. This was
  confusing. Version 0.2 has a single set of species calls.


Indexing:

* Added index files for searching with phylign.


Misc:

* Added file of md5sums ``md5sum.txt`` for all files in the release (except for the READMEs).


Overview
--------


This release 0.2 includes the same 1,932,812 samples as in release 0.1.

More than 1,932,812 samples were originally processed, however
the release is for the samples that successfully resulted in an
assembly with total length between 100kbp and 15Mbp. This means
that some of the metadata files include more samples than the
1,932,812 (see details for each file below).

661,384 of the 1,932,812 are from the "661k" bacteria assemblies dataset
from Blackwell 2021 (https://doi.org/10.1371/journal.pbio.3001421).
The exact original total of the 661k set was 661,405.
21 of these have total length greater than 15Mbp, leaving 661,384 assemblies
included in this release of 1,932,812 samples.

Metadata
--------

The metadata files are in the directory ``metadata/``.

Sample accessions
~~~~~~~~~~~~~~~~~

The 1,932,812 sample accessions are listed in the file
``sample_list.txt.gz``.


Species calls and high quality data set
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The species calls and high quality dataset are generated with
the script ``make_hq_sample_list.py``.
The high quality dataset has 1,858,610 samples.

This script is updated since version 0.1 to expose all parameters
to the user, so it can be rerun with different cutoffs. The defaults
were used to define the high quality dataset here, which meant a sample must
pass all of these requirements to be included as high quality:

* Have a sylph call with at least 99 percent minimum abundance.
  If a sample has more than one call (eg where it has more than one
  run), then require all species calls to be the same
* Minimum checkm2 completeness of 90%
* Maximum checkm2 contamination of 5%
* Total assembly length between 100kbp and 15Mbp
* Maximum number of contigs 2,000
* Minimum N50 2,000

The species calls are in ``species_calls.tsv.gz``, plus a column ``HQ`` with
``T`` (true) or ``F`` (false) showing if each sample was in the high quality
dataset. The high quality sample IDs are also listed in the file
``hq_set.sample_list.txt.gz``. The 74,202 rejected samples are listed in
the file ``hq_set.removed_samples.tsv.gz``, along with the reason(s) why.




Assembly statistics
~~~~~~~~~~~~~~~~~~~

Basic assembly statistics for each assembly are in ``assembly-stats.tsv.gz``.
These were made using ``assembly-stats``
(https://github.com/sanger-pathogens/assembly-stats) git commit 7bdb58b.

These results are a superset of the 1,932,812 samples. To restrict
to the release 0.2 samples, filter on the column ``in_v0.2 == "Y"``.
There is also the column ``in_661k`` to show if each sample is
in the 661k dataset.


Checkm2
~~~~~~~

Checkm2 (https://doi.org/10.1038/s41592-023-01940-w) version 1.0.1 was
run on each assembly. The results are in the file ``checkm2.tsv.gz``.
Checkm2 was only run on the 1,932,812 samples.
The columns in the output file are the original output from checkm2 but
with the first "Name" column replaced with "sample", and then the values
are the INSDC sample accession IDs.

275 samples stopped mid-run, with the error message
"ERROR: No DIAMOND annotation was generated. Exiting". These have
"No DIAMOND annotation was generated" in the ``Additional_Notes`` column, and
all other fields are "NA".



Sylph
~~~~~

Sylph (https://doi.org/10.1101/2023.11.20.567879) version 0.5.1 was
run on the sequencing reads, using the pre-built GTDB r214
database (https://storage.googleapis.com/sylph-stuff/v0.3-c200-gtdb-r214.syldb).

Sylph was run on a superset of the reads from the 1,932,812 samples,
and the results are in ``sylph.tsv.gz``.

The contents of ``sylph.tsv.gz`` is the original sylph output,
except for these differences:

* Extra columns ``in_v0.1``, ``in_661k``, to show which dataset(s) each
  sample belongs to.
* The ``Sample_file`` column was replaced with the INSDC accession columns ``sample`` and ``Run``.
* An extra column ``Species`` was added, which is a species call from the ``Genome_file`` column.

Some reads resulted in no sylph output, presumably because there were
no matches. These 3252 samples are listed in the file
``sylph.no_matches.txt.gz`` and are not present in ``sylph.tsv.gz``.


Human contamination
~~~~~~~~~~~~~~~~~~~

All assemblies were mapped to the human genome CHM13v2:
(https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/009/914/755/GCA_009914755.4_T2T-CHM13v2.0/GCA_009914755.4_T2T-CHM13v2.0_genomic.fna.gz),
plus HLA sequences (``IMGTHLA-3.55.0-alpha/hla_gen.fasta`` from
https://github.com/ANHIG/IMGTHLA/archive/refs/tags/v3.55.0-alpha.zip).

We used ``nucmer`` (from mummer version 4.0.0rc1) with the defaults,
``delta-filter -i 90 -l 100 -m``, and then ``show-coords -dTlro``. The full
results are in ``nucmer_human.gz``.

A contig was counted as human contamination and removed from an
assembly if it had a match that was at least 99% identity and 90% of its total
length. The removed samples/contigs are listed in
``metadata/contam_contigs.json.gz``.



Sequence searching and ANI with sketchlib
-----------------------------------------

Please see the sketchlib section of the README on this ftp site:
https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/indexes/README.md


Sequence searching with Phylign
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Phylign (Břinda *et al*, 2023) allows efficient searching and full alignment of
query sequences to huge datasets of bacterial assemblies that have been
phylogenetically compressed using MiniPhy
(https://github.com/karel-brinda/MiniPhy). We have recently adapted Phylign to
allow users to align query sequences to AllTheBacteria v0.2 or subsets of this
dataset.  Detailed information, including how to run Phylign on computing
clusters, can be found in the README on our GitHub page
(https://github.com/AllTheBacteria/Phylign/blob/main/README.md), and in README
in the relevant directory on this ftp site
(https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/indexes/)


Incremental release 2024-08
===========================

This is an incremental release, adding 507,565 new assemblies.
Sequencing metadata from the ENA was downloaded on 2024-08-01,
and all eligible samples (ie paired Illumina, WGS etc) that were not already
in release 0.2 were processed.
