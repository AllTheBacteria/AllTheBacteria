Annotation
==========

Bakta
-----

All assembled ATB sample genomes were annotated using Bakta `v1.9.4 <https://github.com/oschwengers/bakta/releases/tag/v1.9.4>`_ using its `full` database `v5.1 <https://doi.org/10.5281/zenodo.10522951>`_. Bakta was run in a Conda environment using its public `Bioconda <https://bioconda.github.io/recipes/bakta/README.html>`_ package.

Result files are available on OSF in the `Bakta component <https://osf.io/zt57s/>`_. However, due to the huge amount of raw annotation data (>35 TB), a couple of measures have been taken to handle this. First, only JSON files are provided since all Bakta output files can be restored from those (see below). Second, sample result files are packed in taxonomic batches, just like assembled FASTA files to achieve better compression ratios. Third, since there are OSF data size limits of 50 GB and 5 GB for compartments and files, respectively, all taxonomy batches were further distributed to several compartments. Furthermore, some taxonomy batches had to be split into separate files to meet the 5 GB file limit. By doing so, all annotation data could be reduced to a total of ~1.3 TB and ~0.3 TB for ``r0.2`` and ``incr_release.202408``, respectively.

For each release, there is a status file in a ``File_Lists`` folder, e.g. `atb.bakta.r0.2.status.tsv.gz` providing the following information:

* ``sample`` = the INSDC sample accession
* ``status`` = the status of the Bakta run (``PASS``, ``FAIL``)
* ``file_name`` = the name of the Bakta JSON result file, e.g. `SAMN38372697.bakta.json`
* ``file_md5`` = MD5 sum of `file_name`
* ``tar_xz`` = the name of the tar.xz file where this sample's JSON lives following a fix schema: atb. ``analysis`` . ``release`` . ``batch`` .tar.xz, e.g. `atb.bakta.r0.2.batch.1.tar.xz`
* ``tar_xz_md5`` = MD5 sum of `tar_xz`
* ``tar_xz_size_MB`` = size of the `tar_xz` file in MB

Example `SAMN38372697`::

    sample          SAMN38372697
    status          PASS
    file_name       SAMN38372697.bakta.json
    file_md5        008d86ad046e0d152b8cc22d7452be24
    tar_xz          atb.bakta.incr_release.202408.batch.29.tar.xz
    tar_xz_md5      7da90ac7650de2c2e0b821569ae2a602
    tar_xz_size_MB  1201.0

To restore all output files for a given sample from its JSON file, use the following command::

    bakta_io --output <output-path> --prefix <file-prefix> sample.json

For any questions regarding the Bakta genome annotation, please contact `Oliver Schwengers <mailto:oliver.schwengers@cb.jlug.de>`_.