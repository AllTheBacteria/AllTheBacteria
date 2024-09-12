=============================
Migration from EBI FTP to OSF
=============================

This page has details of moving the data originally hosted at the
`EBI FTP site <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/>`_
to OSF. You probably only want to read this if you used data that
was on the FTP site, and are now looking at the AllTheBacteria project on
OSF and want to know why some file names have changed.
The short explanation is: file names were changed so that they did not have
species names in them.

Spare me the details, I just want old -> new names
==================================================

Assembly tarballs and Phylign index files were renamed.
Here is a TSV file that has all the old and new file names, md5 sums, and OSF
URLs: `atb_ebi_r0.2_ftp_to_osf_rename.tsv <https://osf.io/jkg72>`_. No other filenames were changed.


What was/is on the EBI FTP site?
================================

There was:

* `release 0.1 <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.1/>`_.
  This was the first release of the data, and corresponds to the first
  version of the `preprint <https://www.biorxiv.org/content/10.1101/2024.03.08.584059v1>`_.
  The data have since been withdrawn and replaced by version 0.2.

There is:

* `release 0.2 <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/>`_.
  This is the second release of the data, which is the same as 0.1 but with
  some human contamination contigs removed.

See the :doc:`release history </release_history>` for more details on
releases 0.1 and 0.2. Everything below is describing release 0.2 and what
happened during copying from the FTP site to OSF.

What is on OSF?
===============

All data from release 0.2 are also on OSF. However, some files were renamed
before putting on OSF, so that no species names were in the file names.
We wanted to separate out species calls from the assemblies themselves.
The assemblies will not (or are extremely unlikely to) change.
Species calling is difficult, and we do expect that to change.

Why were species names in the files? Because the compression/indexing processes
needed species calls. It doesn't matter if those calls are wrong, it just helps
to group similar genomes together for compression efficiency.
However, leaving those species names in the file names could be misleading,
especially as species calls will change over time.


Metadata files
==============

These files are all the same. All files in the
`ftp metadata directory <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/metadata/>`_
were copied to OSF, in the
`AllTheBacteria metadata component <https://osf.io/h7wzy/>`_.
Some files may get added to OSF, but all files on FTP were copied over to OSF.



Assembly files
==============

No actual assemblies were changed. All FASTA files are identical between the
EBI ftp site and on OSF. However, the assembly tarball names, and the directory
name that each tarball extracts to, was changed.

This should make sense using an example. This tarball is on the FTP site:
``achromobacter_xylosoxidans__01.asm.tar.xz``.
It extracts to a directory ``achromobacter_xylosoxidans__01/`` containing FASTA
files. In other words, running ``tar xf achromobacter_xylosoxidans__01.asm.tar.xz``
would make these files::

    achromobacter_xylosoxidans__01/SAMN12335635.fa
    achromobacter_xylosoxidans__01/SAMN12335634.fa
    achromobacter_xylosoxidans__01/SAMN12335574.fa
    ...etc

The renamed tarball on OSF is called ``atb.assembly.r0.2.batch.1.tar.xz`` and
it extracts to the directory ``atb.assembly.r0.2.batch.1/``. In other words,
running ``tar xf atb.assembly.r0.2.batch.1.tar.xz`` would make these files::

    atb.assembly.r0.2.batch.1/SAMN12335635.fa
    atb.assembly.r0.2.batch.1/SAMN12335634.fa
    atb.assembly.r0.2.batch.1/SAMN12335574.fa
    ...etc

The extracted files ``SAMN12335635.fa``, ``SAMN12335634.fa``, ``SAMN12335574.fa``,
... are identical bewteen the original and renamed tarballs.
The only difference is the tarball name and directory to which it extracts.
The order of the files inside each tarball was preserved.


Index files
===========

Sketchlib
---------

The `sketchlib files on the FTP site <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/indexes/sketchlib/>`_
were copied with no changes to the OSF
`AllTheBacteria sketchlib component <https://osf.io/rceq5/>`_.


Phylign
-------

The `Phylign files on the FTP site <https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/indexes/phylign/>`_
were renamed on the OSF
`AllTheBacteria Phylign component <https://osf.io/h6xk7/>`_.
The renaming was done to match the assembly renaming.
For example, the file ``achromobacter_xylosoxidans__01.cobs_classic.xz`` on
the FTP site was renamed to ``atb.assembly.r0.2.batch.1.cobs_classic.xz`` on OSF.


Are 15 Phylign files missing?
=============================

No.

You may have noticed that the numbering in the phylign files jumps
from file ``atb.assembly.r0.2.batch.637.cobs_classic.xz`` to
``atb.assembly.r0.2.batch.653.cobs_classic.xz``.
There are no 638-652 phylign files. Why is this...?

When renaming the assembly and phylign files, the old names were
just enumerated, so the first file ``achromobacter_xylosoxidans__01.asm.tar.xz``
was renamed ``atb.assembly.r0.2.batch.1.tar.xz``.
And similarly, the corresponding Phylign old file was
``achromobacter_xylosoxidans__01.cobs_classic.xz``,
and renamed to ``atb.assembly.r0.2.batch.1.cobs_classic.xz``.

The samples with no species call are spread across 15 assembly
tarballs (old name ``unknown__01.asm.tar.xz`` ... ``unknown__15.asm.tar.xz``),
and got new names ``atb.assembly.r0.2.batch.638.tar.xz`` ...
``atb.assembly.r0.2.batch.652.tar.xz``. These samples were not included in
the Phylign index. To keep the numbering consistent when translating:
old assembly tarball <-> old Phylign <-> new assembly tarball <-> new Phylign
file, we left out new Phylign file numbers 638-652.  This means that the
filename numbering for assemblies and Phylign file is consistent and assembly
batch number ``N`` (``atb.assembly.r0.2.batch.N.tar.xz``) corresponds to
Phylign index file number ``N`` (``atb.assembly.r0.2.batch.N.cobs_classic.xz``).
