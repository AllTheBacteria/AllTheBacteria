Antimicrobial Resistance
=========================

AMRFinderPlus
-------------

The results of running AMRFinderPlus for AllTheBacteria are available on OSF in the `AMRFinderPlus component <https://osf.io/7nwrx/>`_. The results are organized into folders based on the version of ``amrfinder`` that was used, and sub-folders within these based on the ``amrfinder database`` version used. The dataset is frequently updated; therefore, we also include sub-folders of the results broken down by the AllTheBacteria release, useful if you just want the results for a new incremental release. The ``latest`` subfolder contains the most recent aggregated results of running on all samples in the AllTheBacteria dataset and can be found here: `AMRFP_results.tsv.gz <https://osf.io/ck7st>`_.

Each table of results has a matched status file. The status file indicates which samples we have run ``amrfinder`` on in the ``sample`` column, whether the run completed successfully (``PASS``), failed (``FAIL``), or is yet to be run (``NOT DONE``) in the ``status`` column. There is an additional column for any comments, such as indicating if the output of ``amrfinder`` was empty if no AMR determinants were identified. We also include a copy of the ``amrfinder`` database we used in each ``database`` sub-folder.

A Snakemake workflow to rerun this analysis can be found on the AllTheBacteria GitHub page `here <https://github.com/AllTheBacteria/AllTheBacteria/tree/main/reproducibility/All-samples/AMR/AMRFinderPlus>`_ and modified fairly easily to use newer software or database versions. If you want to do this and have any questions or need some help, please contact `Daniel Anderson <mailto:dander@ebi.ac.uk>`_.
