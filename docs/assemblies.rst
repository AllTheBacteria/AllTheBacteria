Assemblies
==========

Summary
-------

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

Downloading assemblies
----------------------

The latest list of all samples and their related file names are
in the file `file_list.all.latest.tsv.gz <https://osf.io/4yv85>`_.
This file should have all the information you need.
Older files and files split by dataset are also available - see
the folder "File Lists" in the top level of the `Assembly component on OSF
<https://osf.io/zxfmy/>`_.

The columns in this file are:

* ``sample`` = the INSDC sample accession
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
    filename_in_tar_xz  atb.assembly.incr_release.202408.batch.1/SAMD00555951.fa
    tar_xz              atb.assembly.incr_release.202408.batch.1.tar.xz
    tar_xz_url          https://osf.io/download/66d9a283a8ea15b31e77b451/
    tar_xz_md5          2e5d42de7f7f047245b4c4b78e4dabaf
    tar_xz_size_MB      61.36

The wget command to get the tar file would be::

    wget -O atb.assembly.incr_release.202408.batch.1.tar.xz https://osf.io/download/66d9a283a8ea15b31e77b451/

Extract the FASTA with::

    tar xf atb.assembly.incr_release.202408.batch.1.tar.xz atb.assembly.incr_release.202408.batch.1/SAMD00555951.fa

