Biosynthetic Gene Clusters
==========================

GECCO
-------------

The biosynthetic gene clusters (BGCs) detected by running GECCO (v0.9.8) on AllTheBacteria v0.2 and the incremental release (08-2024) are available on `OSF <https://osf.io/cufb2/>`_. The results include concatenated files of BGCs as GenBank records (``.gbk``) as well as the concatenated ``clusters.tsv`` files with associated information. Due to file size, the ``.gbk`` files have been split (3 files for v0.2 and 2 for the incremental release 08-2024). For further details on what the ``clusters.tsv`` files contain, please see the `GECCO documentation <https://gecco.embl.de>`_. We have provided separate files for the v0.2 release and the incremental release (08-2024), as well as a pair of files which contains both the v0.2 and the incremental release (08-2024).

Also available is a status file indicating which genomes (``samples`` column) have been processed. As of now, that includes all genomes present in release v0.2 and in the incremental release (08-2024), and hence all samples are marked as ``PASS`` in the second column (``status``).

GECCO v0.9.8 was run as a container, which is available on Biocontainers. All scripts used for the analysis are provided on the AllTheBacteria GitHub (add link here). For any questions, please contact `Laura Carroll <mailto:laura.carroll@umu.se>`_.
