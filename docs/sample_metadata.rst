Metadata and QC
===============

Metadata files are all stored on OSF in the AllTheBacteria
`Assembly component <https://osf.io/h7wzy/>`_.

These files all relate to INSDC metadata, tracking which samples have been
processed, and then results of running the assembly (and related tools)
pipeline. They include:

* ENA metadata (this is a snapshot at the time AllTheBacteria was updated to
  add more samples)
* Sample status at a high level: included in AllTheBacteria, or rejected
  for some reason when running the assembly pipeline
* Sylph results on the reads, and species calls made from the Sylph results
* Assembly statistics and checkm2 output
* Nucmer contig matches of aligning to the human genome
* "High quality" samples (defined below)


Latest data for all samples
---------------------------

The latest complete set of data is release 0.2 plus incremental release
2024-08.  The latest metadata files for this set are in the
``Aggregated/Latest_2024-08/`` folder of
the `Assembly component <https://osf.io/h7wzy/>`_.

The latest status of all processed samples is in the file
`status.202408.tsv.gz <https://osf.io/vrekj>`_.
It tracks the result of trying to download the reads, run sylph, assemble,
and then human decontamination.
The columns are:

* Sample: the sample accession (SAM...)
* Status: status of the sample. This is either "PASS", meaning that the pipeline
  finished successfully and we have an assembly, or "FAIL:..." if it failed
  and for what reason
* Dataset: the dataset the sample belongs to
* Comments: any other comments

Older data
----------

We recommend you use the complete data for all samples, since it has
everything in one place. However, older metadata files are also available,
in folders named by release. At the time of writing these are 0.1
(which was replaced by 0.2), 0.2, and incremental release 2024-08.



Metadata files
--------------

Each folder (per dataset, or the latest complete dataset) has the
metadata files described below.


Sample lists
~~~~~~~~~~~~

The file ``sample_list.txt.gz`` lists all samples that have an
assembly. For aggregated data, it is the samples that have
"PASS" in the "Status" column of the status file (described above).

All of the samples in ``sample_list.txt.gz`` will be in the files described
later (sylph, checkm2 etc). Those files will contain more samples because
not every sample results in an assembly. For example, the reads for a given
sample could be downloaded and sylph run successfully, and then the assembly
fails. That sample would have sylph results, but no assembly, and so does not
appear in ``sample_list.txt.gz``.



ENA metadata
~~~~~~~~~~~~

When processing new samples, the first thing we do is download all metadata
from the ENA for all bacteria. The results are in ``ena_metadata.tsv.gz``,
providing a snapshot at the time of download. These files are only included
with each release. We do not make an aggregated file across releases, since
it does not really make sense to do so.


Sylph
~~~~~

After downloading the reads, sylph is run on them to get
species abundances. The results are in the file ``sylph.tsv.gz``, which
is the original sylph output, except for these differences:

* The ``Sample_file`` column is replaced with the INSDC accession columns
  ``Sample`` and ``Run``.
* An extra column ``Species`` is added, which is a species call from the
  ``Genome_file`` column, using GTDB species names.

Some samples have no matches and there is no output - these samples are listed
in the file ``sylph.no_matches.tsv.gz``.

We also try to make a species call from the sylph output, which can be found
in ``species_calls.tsv.gz``. This is made using a simple method and is
likely to contain some errors: if a sample has a sylph match with
more than 99% abundance then that is the species call, otherwise the species
is called as "unknown". This call is used for compressing the assemblies
with Minihpy (it requires species calls), and so incorrect calls do not
matter for this use case.


Decontamination
~~~~~~~~~~~~~~~

After assembly, we use nucmer to align the contigs to the human genome (plus
HLA sequences). Matching contigs are removed from the assembly.
The complete nucmer output is given in ``human_nucmer.gz``. We do not
provide an aggregated nucmer file of the latest data
because it is relatively large.


Assembly statistics
~~~~~~~~~~~~~~~~~~~

The results of running ``assembly-stats``
(from https://github.com/sanger-pathogens/assembly-stats) are provided in
``assembly-stats.tsv.gz``.


Checkm2
~~~~~~~

The results of running ``checkm2`` are provided in ``checkm2.tsv.gz``.
The columns in the output file are the original output from checkm2 but
with the first "Name" column replaced with "Sample", and then the values
are the INSDC sample accession IDs.


High quality dataset
~~~~~~~~~~~~~~~~~~~~

We define a high quality dataset for each release. This is samples that:

* Have a sylph call with at least 99 percent minimum abundance.
  If a sample has more than one call (eg where it has more than one
  run), then require all species calls to be the same
* Minimum checkm2 completeness of 90%
* Maximum checkm2 contamination of 5%
* Total assembly length between 100kbp and 15Mbp
* Maximum number of contigs 2,000
* Minimum N50 2,000

These samples are listed in ``hq_set.samples_list.txt.gz``. The rejected
samples are listed in ``hq_set.removed_samples.tsv.gz``.
