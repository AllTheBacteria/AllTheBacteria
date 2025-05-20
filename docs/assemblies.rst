Assemblies
==========

Summary
-------

Assemblies can be downloaded from OSF, AWS, or the ENA.

* Batched assemblies are on OSF. If you want all assemblies or large numbers
  then get them from OSF.
* Individual FASTA files for each sample are on AWS. If you want assemblies
  for specific samples then AWS will be easiest.
* Individual FASTA files are also available from the ENA. However, around
  10,000 assemblies are not available from the ENA, since the submission
  system rejected them due to various errors.




Downloading assemblies from AWS
-------------------------------

Individual assembly files
^^^^^^^^^^^^^^^^^^^^^^^^^

A gzipped FASTA assembly file for each sample is available, with the S3 URI
of the form::

    s3://allthebacteria-assemblies/<SAMPLE_ID>.fa.gz

For example::

    s3://allthebacteria-assemblies/SAMD00000344.fa.gz


To download to the current working directory using the aws cli::

    aws s3 cp --no-sign-request s3://allthebacteria-assemblies/SAMD00000344.fa.gz .


The object URL is of the form::

    https://allthebacteria-assemblies.s3.eu-west-2.amazonaws.com/<SAMPLE_ID>.fa.gz

For example::

    https://allthebacteria-assemblies.s3.eu-west-2.amazonaws.com/SAMD00000344.fa.gz


Download with wget::

    wget https://allthebacteria-assemblies.s3.eu-west-2.amazonaws.com/SAMD00000344.fa.gz


List of all available assemblies
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you want to know which assemblies are on AWS, we do not recommend running
``ls`` to find out! It will be slow.
Every Monday, a list of current assembly files is generated. Get the latest
file with::

    aws s3 ls --no-sign-request s3://allthebacteria-metadata/allthebacteria-assemblies/assemblies-list/data/  | sort | tail -n1

At the time of writing, the output was::

    2025-03-23 17:38:59   79359181 b21b76f7-b5f1-4862-ba55-4b515bc6d05f.csv.gz

That file can be downloaded to a file called ``latest.tsv.gz`` with::

    aws s3 cp --no-sign-request s3://allthebacteria-metadata/allthebacteria-assemblies/assemblies-list/data/b21b76f7-b5f1-4862-ba55-4b515bc6d05f.csv.gz latest.tsv.gz

or::

    wget -O latest.tsv.gz https://allthebacteria-metadata.s3.eu-west-2.amazonaws.com/allthebacteria-assemblies/assemblies-list/data/b21b76f7-b5f1-4862-ba55-4b515bc6d05f.csv.gz

That file lists all assemblies that are in the bucket ``allthebacteria-metadata``,
plus the size, md5sum, and time of upload.


Downloading assemblies from the ENA
-----------------------------------

Nearly all of the assemblies have been accessioned in the ENA
as "analysis" objects. The accessions are in the file
``atb.metadata.202408.sqlite.assembly.tsv.xz``. It is a TSV format file of
the table ``assembly`` from the :doc:`SQLite metadata database </metadata_sqlite>`.
The TSV file can be downloaded with::

  wget -O atb.metadata.202408.sqlite.assembly.tsv.xz https://osf.io/download/sdx5m/

The relevant columns here are ``sample_accession`` and ``assembly_accession``.
For example, sample ``SAMN23010837`` has the assembly accession
``ERZ26049045``. Get the URL by querying the ENA::

    $ wget -qO- 'https://www.ebi.ac.uk/ena/portal/api/filereport?accession=ERZ26049045&result=analysis'
    analysis_accession	submitted_bytes	submitted_md5	submitted_ftp
    ERZ26049045	1785435	1e59b0bf2e684f6491d9617dee9fde2b	ftp.sra.ebi.ac.uk/vol1/analysis/ERZ260/ERZ26049045/SAMN23010837.fa.gz

and then get the assembly with::

    wget ftp.sra.ebi.ac.uk/vol1/analysis/ERZ260/ERZ26049045/SAMN23010837.fa.gz



Downloading assemblies from OSF
-------------------------------

FASTA files of assemblies for AllTheBacteria are available from
OSF. To reduce file size, the assemblies are provided in batches of
xzipped tar archives (made by
`Miniphy <https://github.com/karel-brinda/MiniPhy>`_).
Each archive contains up to ~4000 FASTA files.

The downside of this is that if you want the assembly for a single
sample, then you will need to download the tar.xz file and extract
it from that. We apologise for the inconvenience, but bear in mind
that miniphy compression makes a huge difference. For example, the
size of the individual gzipped FASTA files for release 0.2 is
around 3.1TB. This is too large to sensibly put on OSF.
The total size of the same data but in compressed archive files is 89GB.

The latest list of all samples and their related file names are
in the file `file_list.all.latest.tsv.gz <https://osf.io/4yv85>`_.
This file should have all the information you need.
Older files and files split by dataset are also available - see
the folder "File Lists" in the top level of the `Assembly component on OSF
<https://osf.io/zxfmy/>`_.

The columns in this file are:

* ``sample`` = the INSDC sample accession
* ``species_sylph`` = inferred species call from running sylph on the reads (see below)
* ``species_miniphy`` = the name miniphy gave to the species (see below)
* ``filename_in_tar_xz`` = the FASTA filename for this sample inside the tar.xz file
* ``tar_xz`` = the name of the tar.xz file where this sample's FASTA lives
* ``tar_xz_url`` = URL of `tar_xz`
* ``tar_xz_md5`` = MD5 sum of `tar_xz`
* ``tar_xz_size_MB`` = size of the `tar_xz` file in MB

If you want to download the archives in bulk, then use the
``tar_xz_url`` column to get the urls, and ``tar_xz`` for what
you should name the downloaded file. OSF does not have the
filename in the download URL.

Here's an example of how to get the wget commands to run::

    $ zcat file_list.all.latest.tsv.gz  | awk 'NR>1 {print "wget -O "$3" "$4}' | uniq | head -n3
    wget -O atb.assembly.r0.2.batch.1.tar.xz     https://osf.io/download/667142936b6c8e33f404cce7/
    wget -O atb.assembly.r0.2.batch.2.tar.xz https://osf.io/download/667142d10f8c8017b03c96b0/
    wget -O atb.assembly.r0.2.batch.3.tar.xz https://osf.io/download/667142c877ff4c5f1ee04625/

If you just want one sample, for example sample SAMD00555951,
then this is the info in `file_list.all.latest.tsv.gz <https://osf.io/4yv85>`_::

    sample              SAMD00555951
    species_sylph       Acinetobacter baumannii
    species_miniphy     acinetobacter_baumannii
    filename_in_tar_xz  atb.assembly.incr_release.202408.batch.1/SAMD00555951.fa
    tar_xz              atb.assembly.incr_release.202408.batch.1.tar.xz
    tar_xz_url          https://osf.io/download/66d9a283a8ea15b31e77b451/
    tar_xz_md5          2e5d42de7f7f047245b4c4b78e4dabaf
    tar_xz_size_MB      61.36

The wget command to get the tar file would be::

    wget -O atb.assembly.incr_release.202408.batch.1.tar.xz https://osf.io/download/66d9a283a8ea15b31e77b451/

Extract the FASTA with::

    tar xf atb.assembly.incr_release.202408.batch.1.tar.xz atb.assembly.incr_release.202408.batch.1/SAMD00555951.fa


Species calls and assembly batches
----------------------------------

Why are species calls included in the assembly file? For convenience, to allow
getting all assemblies for a particular species. Note that one batch
of assemblies will often contain the same species.

Miniphy needs species calls to aid compression of the assembly FASTA files,
so that similar genomes are batched together.
We run Sylph on all reads, to get this species call for each sample.
See the :doc:`Sylph section </species_id>` of the species page for details.
The calls input to Miniphy are in the column ``species_sylph``.
Miniphy changes these names (removing spaces, adding underscores) - we
put the Miniphy name in ``species_miniphy`` column.

Miniphy keeps its species names in its output files. However, for AllTheBacteria
we want to keep species calls separate from assembly files. For this reason,
we rename the miniphy files before releasing them.
(Side note: release 0.2 on the EBI FTP site did have species names in them,
but were removed while :doc:`migrating to OSF </ebi2osf>`.)
