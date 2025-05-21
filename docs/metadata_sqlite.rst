SQLite metadata
===============

This page describes the state of the metadata for all samples as of
2024-08-01.  It is collated into an SQLite database.

This is very detailed; if you just want simple flat files, then
please see the :doc:`Metadata and QC </sample_metadata>` page.

The SQLite database is in the file
``atb.metadata.202408.sqlite.xz``, available from OSF at:
https://osf.io/f9jeh

Download in a terminal with::

    wget -O atb.metadata.202408.sqlite.xz https://osf.io/download/f9jeh/


It has:

* metadata from the ENA
* the status of all samples (assembled, assembly failed, not processed etc)
* sylph results
* assembly statistics (N50 etc)
* checkm2 results

The details here are important and quite complicated, and there are
many different cases to consider within the metadata.
We recommend you read this whole page carefully
if you want to fully understand the how we processed the samples in
release 0.2 and incremental release 202408.

Note that the SQLite file ``atb.metadata.202408.sqlite.xz`` on OSF is compressed
in xz format, and is approximately 1.5GB.
It will need to be decompressed to use it, with a size of around 17GB.


Background
----------

AllTheBacteria is an extension of the 2021 "661k" project from Blackwell et al:
we started with the set of samples/assemblies used in the 661k.
AllTheBacteria adds to the 661k
by processing all samples in the ENA that pass metadata checks and are not
already in the 661k. The resulting new assemblies are added to the
set of existing 661k assemblies.

The original 661k project and AllTheBacteria both used data dumped from
the ENA to identify samples and sequencing runs for assembly.
As of August 2024, we have three sources of ENA metadata: the supplementary
file from the 661k paper, and dumps of ENA metadata taken on
2024-06-25 and 2024-08-01.

For AllTheBacteria, assemblies were processed in batches. There was an initial
batch in 2023, then two more batches 2024-06-25 and 2024-08-01. Each time, using
ENA metadata. Note that we do not have the ENA dump from
2023, but do have a lookup of sample to run for each assembled sample.
For each new batch, we simply asked: for each sample, have we processed it
already, and if not then does it have exactly one sequencing run we can use?
If the answer was yes, then it was processed.

Unfortunately, it turns out that metadata can and does change.
For example, runs or samples can be suppressed, a run could change which
sample it links to, or FASTQ files (and therefore md5sum) can change.
And at the same time, the last updated field can remain constant.
This complicates things, especially
as we discovered the changeable nature of the metadata
after releasing the incremental release 202408.

The SQLite database gathers all this information together, and includes
a summary table of all known samples. This documents whether each
sample was processed, which runs were used, and results of stringent
metadata checks across all of our metadata sources. Essentially, we now
require a sample to pass all our metadata checks, and
remain consistent across all the sources of metadata.
We have been intentionally paranoid, preferring to flag up anything unusual
at the expense of potentially rejecting  more samples than is necessary.

This analysis does not redefine either release 0.2 or incremental release
202408. These assemblies are all still available from OSF and AWS. No
assemblies have been added or removed. However, we now
identify samples that were not previously flagged, because
the new checks are more stringent. In particular, one reason for this is
failing to accession an assembly in the ENA. The ENA rejects a submission
if the sample's metadata fails various checks. This is out of our control,
meaning that there are assemblies in release 0.2 and/or
incremental release 202408 that are not in the ENA, and only available from
OSF and AWS.


Metadata checks
---------------

For the 661k set, we can infer which run(s) were used for each sample for
assembly using the 661k supplementary data, and the rules used to choose
runs. The rules were: ``instrument_platform`` not ``PACBIO_SMRT`` or
``OXFORD_NANOPORE``; ``library_source`` not ``METAGENOMIC`` or
``TRANSCRIPTOMIC``; and ``*_1.fastq.gz`` and ``*_2.fastq.gz`` files must
exist. Samples with more than one sequencing run were allowed.

More stringent rules were used for new samples in AllTheBacteria.
This means there are samples in the 661k set that would not be used if they
were new and being considered for AllTheBacteria.
For AllTheBacteria, we required ``instrument_platform`` = ``ILLUMINA``,
``library_strategy`` = ``WGS``, ``library_source`` = ``GENOMIC``,
``library_layout`` = ``PAIRED``, and ``*_1.fastq.gz`` and ``*_2.fastq.gz``
files must exist. There must also be exactly one sequencing run that
passes for a given sample.
We also know exactly which run was used for each sample that was assembled.


SQLite database
---------------

ENA metadata tables
^^^^^^^^^^^^^^^^^^^

There are three ENA metadata tables in the database: ``ena_661k``,
``ena_20240625`` and ``ena_20240801``.
The ``ena_20240625`` and ``ena_20240801`` tables are unedited dumps
of all bacteria sequencing runs from the ENA. The query used was::

    curl -Ss "https://www.ebi.ac.uk/ena/portal/api/search?result=read_run&fields=ALL&query=tax_tree(2)&format=tsv"


The 661k supplementary files are here on Figshare:
https://doi.org/10.6084/m9.figshare.16437939.v1.
The 661k table ``ena_661k`` in the database is generated from the supplementary
file ``Json1_ENA_metadata.json.gz``.
Note that we were unable to use the file ``File9_all_metadata_ena_661K.txt``
because it has one line per sample, and where a sample had more than
one run it is not always possible to get some key information such as the
platform of each run when there is a mix of platforms.
The file ``Json1_ENA_metadata.json.gz`` is a subset of all ENA fields (but
does contain all the ones we need here), so has fewer columns than the
other two ENA tables.

Column names in these tables are the same as those used in the dump
of data from the ENA. In all three tables ``run_accession`` is the primary
key.


Run table
^^^^^^^^^

The SQLite database has a table ``run`` containing
all 3,114,241 runs found in at least one of
the three ENA metadata tables.
It is a summary of pass/fail of the metadata checks, and which of the
ENA tables the run was found in.

The columns are:

* ``run_accession``: ENA run accession. Primary key for the table.
* ``sample_accession``: ENA sample accession. Where the run matches more than
  one sample, it is a comma-separated list of samples.
* ``in_661k``: ``0`` or ``1`` to show if this run is in the ``ena_661k`` table
* ``in_ena_20240625``: ``0`` or ``1`` to show if this run is in the ``ena_20240625``
  table
* ``in_ena_20240801``: ``0`` or ``1`` to show if this run is in the ``ena_20240801``
  table
* ``fastq_md5``: if known, the ``fastq_md5`` entry from ENA metadata. Some FASTQ
  files have changed, in which case this says "multiple" instead of a list of
  different md5 sums (we don't want to use these runs anyway)
* ``meta_pass_atb``: ``0`` or ``1`` to show if this run passes AllTheBacteria
  metadata checks (described above)
* ``meta_pass_661k``: ``0`` or ``1`` to show if this run passes 661k metadata
  checks (described above)
* ``pass``: ``0`` or ``1`` to show overall if this run passes all checks. The
  reasons for a fail are listed below.
* ``comments``: any useful comments related to why a run failed a check.


A run will have ``pass`` = ``0`` if one (or more) of the following is true:

* The run fails one or both of ``meta_pass_atb``, ``meta_pass_661k``
* The run matches more than one sample
* The sample that the run matches changed between ENA metadata tables
* It is not in the 20240801 ENA metadata - ie it used to be available, but
  now it is unavailable
* One or more of the values of ``fastq_md5``, ``fastq_bytes``, ``base_count``
  has changed between ENA metadata tables. Changed values are common in many
  of the fields, which we ignore, but these three are critical because they
  mean that the FASTQ files have changed.


Assemblies/Samples table
^^^^^^^^^^^^^^^^^^^^^^^^

The sample/assemblies table is called ``assembly`` and
contains the union all samples found in the table ``runs`` and all
processed samples in AllTheBacteria releases.
There were samples obtained in 2023 (and assembled and included in release 0.2)
that do not appear in the ENA data dumps 20240625 or 20240801.

The columns of the table are:

* ``sample_accession``: the ENA sample accession. Primary key.
* ``run_accession``: the run accession(s) used when processing this sample and
  making the assembly. This is NOT all run(s) associated with the sample.
  Where there is more than one run, it is a comma-separated list.
* ``assembly_accession``: this is the ENA assembly accession if the assembly
  was successfully submitted to the ENA, otherwise it is ``NA``.
* ``assembly_seqkit_sum``: the output of running ``seqkit sum`` on the
  assembly.
* ``filter``: a list of filters that this sample fails, or ``PASS`` if it passed
  all filters (similar to how the VCF filter column works). This reflects the
  new filters, not those used initially to find samples to process. This means
  a sample could be in the 661k, release 0.2 or incremental release 202408
  but not have ``PASS`` in this column.
* ``asm_fasta_on_osf``: ``0`` or ``1`` to indicate if an assembly FASTA file
  of this sample is available on OSF (and also AWS).
  This corresponds exactly to the assemblies in
  release 0.2 plus incremental release 202408. See comments for the ``filter``
  column - a sample could fail the filter, but still have ``1`` in this column.
* ``dataset``: the dataset to which the sample belongs.
  Note: release 0.2 includes all of the 661k assemblies.
  However, in this table we explicitly say
  which samples are in the 661k data set. Meaning that "r0.2" in this field
  means the sample is in release 0.2 but is not in the 661k set. Samples in the
  original 661k set have "661k" in this column.
* ``comments``: any comments related to reasons for filter fails.


These are the possible filters in the ``filter`` column due to metadata fails:

* ``NO_RUNS``: there are no runs that pass all checks, ie have ``pass`` = ``1``
  in the ``run`` table. It does not mean that there are literally zero
  runs for the sample. It means there were no runs that we could reliably use.
* ``RUN_REMOVED``: the run(s) that were used for the assembly are no longer
  available.
* ``RMMS``: this stands for "Run Matches Multiple Samples". For each run
  matching this sample, we then look up that run's samples. If there is
  more than one matching sample in total across all runs, then
  this filter is added. It means there is ambiguity (or a mistake), instead
  of a one-to-one mapping of sample to/from run.
* ``META_FAIL``: the sample has one or more runs that failed one or more
  AllTheBacteria metadata checks, but those runs were used in the 661k dataset.
* ``RUN_CHANGE``: the run used for this assembly is now linked to a different
  sample.

Samples that passed the metadata filters can then fail during the assembly
pipeline. The filters are:

* ``ASM_DLR``: downloading the reads failed.
* ``ASM_SYL``: sylph failed. This is actually because the downloaded
  FASTQ files are truncated (despite having the correct md5 sum) and causes
  sylph to crash. In future, the pipeline checks for this by checking that
  FASTQ files are valid gzip files.
* ``ASM_SHV``: shovill failed.
* ``ASM_LEN``: the assembly is too long or short.
* ``ASM_TIME``: the pipeline hit the time limit of 1000 minutes before
  finishing.

When an assembly is submitted to the ENA for accessioning, the ENA runs
various metadata checks on the sample. It is possible for the assembly
to then be rejected. If this happens then it gets the filter
``ENA_ASM_SUBMIT_ERR``. We used the bulk submission tool from here:
https://github.com/enasequence/ena-bulk-webincli. Samples were rejected
for various reasons, which are added to the ``comments`` field of the
``assembly`` table. These were shortened in the table. The meaning of
the most common are:

* ``error_organism_not_submittable_XYZ`` - the error was of the form ``ERROR: Organism is not Submittable: XYZ``, where "XYZ" is the name of a genus. This accounts for
  around half of the errors.
* ``error_serovar_only_occur_once`` - the error was: ``ERROR: Qualifier "serovar" may occur only once for feature "source", not "2".``
*  ``no_run_in_ENA`` - the error was one of a few saying that the run was unknown or cannot be referenced
* ``error_qualifier_collection_date_only_occur_once`` - the error was: ``ERROR: Qualifier "collection_date" may occur only once for feature "source", not "2".``
* ``error_strain_must_exist_when_substrain_exists`` - the error was: ``ERROR: The qualifier "strain" must exist when qualifier "sub_strain" exists within the same feature.``
* ``error_multiple_strain_isolate__qualifiers`` - the error was: ``ERROR: Multiple Strain/Isolate qualifiers are not allowed in source feature.``
* ``error_env_sample_and_strain_cannot_exist_together`` - the error was: ``ERROR: Qualifiers environmental_sample and strain cannot exist together.``
* ``error_serovar_only_exist_if_taxon_division_has_values_PRO`` - the error was: ``ERROR: Qualifier "serovar" can only exist if taxonomic division has one of the values "PRO".``
* ``error_variety_only_exist_if_taxon_division_PLN_FUN`` - the error was: ``ERROR: Qualifier "variety" can only exist if taxonomic division has one of the values "PLN,FUN".``
* ``error_isolation_source_only_occur_once`` - the error was: ``ERROR: Qualifier "isolation_source" may occur only once for feature "source", not "2".``
* ``error_cultivar_only_exist_if_taxon_division_PLN`` - the error was: ``ERROR: Qualifier "cultivar" can only exist if taxonomic division has one of the values "PLN".``


There is also the filter ``NOT_PROCESSED``, which is for samples that
are not in release 0.2 or incremental release 202408.
There are some samples that do pass all the metadata checks, but were not
processed. These will be processed in a future release of AllTheBacteria.
The main reason is that we discovered a bug in the Python script that parses
the ENA TSV file, causing it to silently skip over a few hundred
records. If you are using Python's ``csv.DictReader`` to parse the file,
then use the options ``quotechar=None`` and  ``quoting=csv.QUOTE_NONE`` to
avoid this bug.



Sylph table
^^^^^^^^^^^

The table ``sylph`` has all sylph results from all runs of sylph that
produced an output.  Sequencing runs that had no sylph matches are not in
this table.  This table includes sequencing runs that have since been
suppressed/removed from the ENA.

The columns in this table are directly from the sylph output, except:

* The ``Sample_file`` column is replaced with the INSDC accession column ``run_accession``
* An extra column ``Species`` is added, which is a species call from the
  ``Genome_file`` column, using GTDB species names.


Assembly statistics table
^^^^^^^^^^^^^^^^^^^^^^^^^

The results of running ``assembly-stats``
(from https://github.com/sanger-pathogens/assembly-stats) on all assemblies
are in the table ``assembly_stats``.

The columns in this table are taken directly from ``assembly-stats`` output,
except the ``filename`` column is replaced with ``sample_accession``, which
is the primary key for the table.


Checkm2 table
^^^^^^^^^^^^^

The table ``checkm2`` has results of running checkm2 on the assemblies.
The columns in the output file are the original output from checkm2 but
with the first ``Name`` column replaced with ``sample_accession``, which is
the primary key for the table.
There is also an extra column
``Additional_Notes`` that contains the reason for any failed runs, in
which case all fields except for ``sample_accession`` and ``Additional_notes``
are ``null``.


Example SQLite queries
----------------------

Get all samples that have an assembly on OSF/AWS, ie this is
release 0.2 (which includes 661k) and incremental release 202408::

    SELECT * FROM assembly WHERE asm_fasta_on_osf=1;


Get the sample and ENA assembly accessions of all samples in incremental
release 202408 that have an ENA accession::

    SELECT sample_accession,assembly_accession
    FROM assembly
    WHERE dataset="Incr_release.202408" AND assembly_accession !="NA";


Get all samples with an assembly on OSF/AWS with N50 at least 1000000::

    SELECT assembly.sample_accession, assembly.dataset, assembly_stats.total_length, assembly_stats.N50
    FROM assembly JOIN assembly_stats ON assembly.sample_accession = assembly_stats.sample_accession
    WHERE assembly_stats.N50 > 1000000 AND assembly.asm_fasta_on_osf=1;


Get the assembly info and ENA 20240801 metadata for sample SAMN02391170::

    SELECT * FROM assembly
    JOIN ena_20240801 ON assembly.sample_accession = ena_20240801.sample_accession
    WHERE assembly.sample_accession = "SAMN02391170";


In a terminal (not SQLite prompt), dump the assembly table to a tab-delimited
file::

    sqlite3 -header atb.metadata.202408.sqlite -cmd '.mode tabs' 'select * from assembly' > assembly.tsv

