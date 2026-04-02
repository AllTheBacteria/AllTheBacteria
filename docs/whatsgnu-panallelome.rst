WhatsGNU Protein Allele Frequencies
====================================

WhatsGNU computes the frequency of each protein allele across all bacterial genomes.
For every protein in a query genome, the WhatsGNU score (GNU score) reports how many
of the 2,438,285 AllTheBacteria genomes carry an identical copy of that protein sequence.

This is useful for identifying conserved versus rare alleles, understanding species-level
protein diversity, and contextualising novel genomes against all publicly available bacterial data.

What is available
-----------------

The pre-built WhatsGNU database covers 2,438,285 genomes from AllTheBacteria
(release 0.2 plus incremental release 2024-08). It is built from the Bakta protein
annotations (``.faa`` files).

The following files are available on the `WhatsGNU OSF component <https://osf.io/6jr4u/>`_:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Folder
     - Description
   * - ``WGNU_ATB_DB/``
     - Pre-built LMDB database (8 count shards, 8 posting shards, genome-to-species
       index, function lookup table, Sample-to-ID mapping, build metadata). Required for querying.
   * - ``Sample_tables/``
     - List of included genomes (``final_2438285_genomes.txt``), species statistics, and per-genome/per-species
       allele record counts.
   * - ``ATB_hash_seq/``
     - Hash-to-amino-acid-sequence lookup table, split into 20 xz-compressed parts
       (``hash_to_sequence_part_00.xz`` – ``part_19.xz``).
   * - ``ATB_summary_figures_tables/``
     - Publication figures, per-species GNU histograms, allele frequency tables,
       species-sharing networks, coverage estimates, cross-species allele analyses,
       and the pre-computed counts cache.
   * - ``panallelome_summary.txt``
     - Summary results for 2.4M genomes.
   * - ``panallelome_summary.html``
     - Summary results with selected summary figures for 2.4M genomes.

Installation
------------

**Option A — Conda (recommended, once available on bioconda)**

.. code-block:: bash

   conda install -c bioconda whatsgnu-atb

**Option B — pip**

.. code-block:: bash

   pip install whatsgnu-atb

**Option C — From source**

.. code-block:: bash

   git clone https://github.com/microbialARC/WhatsGNU-ATB.git
   bash WhatsGNU-ATB/setup_whatsgnu_atb.sh
   conda activate whatsgnu-atb

Downloading the database
------------------------

Use the included downloader to fetch data from OSF. No OSF account or token is
required — the project is public.

**Download the database (required for querying):**

.. code-block:: bash

   python WhatsGNU-ATB/scripts/download_osf.py \
       --folder WGNU_ATB_DB \
       --out-dir ./WGNU_ATB_DB

**Download everything:**

.. code-block:: bash

   python WhatsGNU-ATB/scripts/download_osf.py \
       --all \
       --out-dir ./WGNU_ATB_DB

**List available folders:**

.. code-block:: bash

   python WhatsGNU-ATB/scripts/download_osf.py --list

The downloader skips files that have already been downloaded with the correct size,
so it is safe to rerun if a download is interrupted.

Querying a genome
-----------------

Your input must be a protein FASTA (``.faa``) file. If your genome
has not yet been annotated with Bakta, see the :doc:`annotation` documentation.

Basic query (GNU scores only)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python WhatsGNU-ATB/scripts/Query_WhatsGNU_ATB.py \
       --db_dir WGNU_ATB_DB \
       --shards 8 \
       --faa your_genome.bakta.faa \
       --out_dir results/

This produces ``your_genome.bakta.faa.whatsgnu.tsv`` with one row per protein,
including its BLAKE2b hash and GNU score.

Full query (with species breakdown and genome similarity)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: bash

   python WhatsGNU-ATB/scripts/Query_WhatsGNU_ATB.py \
       --db_dir WGNU_ATB_DB \
       --shards 8 \
       --faa your_genome.bakta.faa \
       --include_sequence \
       --with_postings \
       --samples_tsv WGNU_ATB_DB/samples_with_ids.tsv \
       --species_names_tsv WGNU_ATB_DB/samples_with_ids.tsv \
       --top_k_species 5 \
       --top_k_genomes 10 \
       --out_dir results/

Querying multiple genomes
^^^^^^^^^^^^^^^^^^^^^^^^^

Pass a directory of ``.faa`` files instead of a single file:

.. code-block:: bash

   python WhatsGNU-ATB/scripts/Query_WhatsGNU_ATB.py \
       --db_dir WGNU_ATB_DB \
       --shards 8 \
       --faa directory_of_faa_files/ \
       --include_sequence \
       --with_postings \
       --out_dir results_batch/

Output files
------------

.. list-table::
   :header-rows: 1
   :widths: 35 65

   * - File
     - Description
   * - ``<sample>.whatsgnu.tsv``
     - Per-protein results: protein ID, BLAKE2b allele hash, GNU score (allele
       frequency across 2.4M genomes), and optionally the amino acid sequence and
       top species contributing to each allele.
   * - ``<sample>.similarity.tsv``
     - Genome similarity report: ranks the genomes in AllTheBacteria that share
       the most protein alleles with the query, with species information and
       percentage of query proteome shared (requires ``--with_postings``).

Interpreting GNU scores
-----------------------

The GNU score for a protein is the number of genomes (out of 2,438,285) that contain
an identical copy of that exact amino acid sequence:

- **High GNU score** (e.g. >100,000): a highly conserved allele found across many genomes and likely multiple species.
- **Moderate GNU score** (e.g. 1000–100,000): a common allele, often species- or genus-specific.
- **Low GNU score** (e.g. 1–100): a rare allele, possibly strain-specific or recently evolved.
- **GNU score = 0**: unique to your query genome — not found in any other AllTheBacteria genome.

Hash-to-sequence lookup
-----------------------

The ``ATB_hash_seq/`` folder contains the mapping from each allele hash to its full
amino acid sequence, split into 20 compressed parts. To reassemble:

.. code-block:: bash

   python WhatsGNU-ATB/scripts/download_osf.py \
       --folder ATB_hash_seq \
       --out-dir ./whatsgnu_db

   cd whatsgnu_db/ATB_hash_seq/
   cat hash_to_sequence_part_*.xz | xz -d > hash_to_sequence.tsv

Building a custom database
--------------------------

To build a new database from your own set of genomes, use ``WhatsGNU_ATB_DB.py``.
See the `GitHub repository <https://github.com/microbialARC/WhatsGNU-ATB>`_ for
full build documentation, including resumable builds, local scratch options, and
all available parameters.

Reproducibility
---------------

Full methods, commands, software versions, and all scripts used to build the
AllTheBacteria WhatsGNU database are available in the
`GitHub reproducibility directory
<https://github.com/AllTheBacteria/AllTheBacteria/tree/main/reproducibility/All-samples/whatsgnu-panallelome>`_.

Citation
--------

If you use WhatsGNU-ATB in your research, please cite:

   Moustafa AM and Planet PJ. WhatsGNU: a tool for identifying proteomic novelty.
   *Genome Biology*, 2020. `doi:10.1186/s13059-020-01965-w <https://doi.org/10.1186/s13059-020-01965-w>`_

   AllTheBacteria — all bacterial genomes assembled, available and searchable.
   *bioRxiv*, 2024. `doi:10.1101/2024.03.08.584059 <https://doi.org/10.1101/2024.03.08.584059>`_
