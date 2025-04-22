Sequence alignment with LexicMap
================================

`LexicMap <https://github.com/shenwei356/LexicMap>`__ is a nucleotide sequence alignment tool
for efficiently querying gene, plasmid, viral, or long-read sequences (>100bp)
against up to millions of prokaryotic genomes.

There are three ways to perform sequence alignment on AllTheBacteria assemblies with LexicMap:

* :ref:`​searching-on-aws-ec2` - Use the pre-built index hosted on AWS
* :ref:`local-search-with-pre-built-index` - Download the index from AWS and search locally
* :ref:`building-an-index-and-searching-locally` - Download assemblies from OSF and build an index

.. _​searching-on-aws-ec2:

​Searching on AWS EC2
---------------------

1. `Launch an EC2 instance <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/LaunchingAndUsingInstances.html>`__
   **in Europe London region (eu-west-2)** where the index is located.

   -  OS: Amazon Linux 2023 64-bit (**Arm**)
   -  Instance type (You might need to `increase the limit of CPUs <http://aws.amazon.com/contact-us/ec2-request>`__):

      -  c7g.8xlarge (32 vCPU, 64 GiB memory, 15 Gigabit, 1.3738 USD per Hour)
      -  c6gn.12xlarge (48 vCPU, 96 GiB memory, 75 Gigabit, 2.46 USD per Hour) (**recommended**)

   -  Storage: 20 GiB General purpose (gp3), only for storing queries and results.

2. `Connect to the instance via online console or a ssh client <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/connect.html>`__.

3. Mount the LexicMap index with `mount-s3 <https://github.com/awslabs/mountpoint-s3>`__ (it’s fast but still slower than local disks).

   ::

       # Install mount-s3. You might need to replace arm64 with x86_64 for other architectures
       wget https://s3.amazonaws.com/mountpoint-s3-release/latest/arm64/mount-s3.rpm
       sudo yum install -y ./mount-s3.rpm
       rm ./mount-s3.rpm

       # Mount the v0.2+202408 index
       mkdir -p atb.lmi
       UNSTABLE_MOUNTPOINT_MAX_PREFETCH_WINDOW_SIZE=65536 \
           mount-s3 --read-only --prefix 202408/ allthebacteria-lexicmap atb.lmi --no-sign-request

4. Install LexicMap.

   ::

       # Check the latest version here: https://github.com/shenwei356/LexicMap/releases
       # You can also check the pre-release here: https://github.com/shenwei356/LexicMap/issues/10
       # Binary's path depends on the architecture of the CPUs: amd64 or arm64
       wget https://github.com/shenwei356/LexicMap/releases/download/v0.7.0/lexicmap_linux_arm64.tar.gz

       mkdir -p bin
       tar -zxvf lexicmap_linux_arm64.tar.gz -C bin
       rm lexicmap_linux_arm64.tar.gz

5. `Upload queries <https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/linux-file-transfer-scp.html>`__.

   ::

       # Here, we use a demo query
       wget https://github.com/shenwei356/LexicMap/raw/refs/heads/main/demo/bench/b.gene_E_faecalis_SecY.fasta

6. Run LexicMap (`tutorial <https://bioinf.shenwei.me/LexicMap/tutorials/search/>`__).

   ::

       # Create and enter a screen session
       screen -S lexicmap

       # Run
       #   Searching with b.gene_E_faecalis_SecY.fasta takes 20 minutes with c7g.8xlarge, 12.5 minutes with c6gn.12xlarge
       #   Searching with b.gene_E_coli_16S.fasta      takes 1h54m with c6gn.12xlarge.
       lexicmap search -d atb.lmi b.gene_E_faecalis_SecY.fasta -o query.lexicmap.txt.gz --debug

7. Unmount the index.

   ::

       sudo umount atb.lmi


.. _local-search-with-pre-built-index:

Local search with pre-built index
---------------------------------


Install ``awscli`` via conda.

::

   conda install -c conda-forge awscli

Test access.

::

   aws s3 ls s3://allthebacteria-lexicmap/202408/ --no-sign-request

   # output
                               PRE genomes/
                               PRE seeds/
    2025-04-08 16:39:17      62488 genomes.chunks.bin
    2025-04-08 16:39:17   54209660 genomes.map.bin
    2025-04-08 22:32:35        619 info.toml
    2025-04-08 22:32:36     160032 masks.bin

Download the index (it’s 5.24 TiB!!!, make sure you have enough disk space).

::

   aws s3 cp s3://allthebacteria-lexicmap/202408/ atb.lmi --recursive --no-sign-request

   # dirsize atb.lmi
   atb.lmi: 5.24 TiB (5,758,875,365,595)
     2.87 TiB      seeds
     2.37 TiB      genomes
    51.70 MiB      genomes.map.bin
   156.28 KiB      masks.bin
    61.02 KiB      genomes.chunks.bin
        619 B      info.toml

`Install <https://bioinf.shenwei.me/LexicMap/installation/>`__ and `search <https://bioinf.shenwei.me/LexicMap/tutorials/search/>`__ with LexicMap.


.. _building-an-index-and-searching-locally:

Building an index and searching locally
---------------------------------------

**Make sure you have enough disk space, at least 8 TB, >10 TB is preferred.**

Tools:

-  `LexicMap <https://bioinf.shenwei.me/LexicMap/installation/>`__
-  https://github.com/shenwei356/rush, for running jobs in parallel

Steps:

1. Downloading the list file of all `assemblies <https://osf.io/zxfmy/>`__ in the latest version (v0.2 plus incremental versions).

   ::

       mkdir -p atb;
       cd atb;

       # Attention, the URL might changes,
       # please check in the browser: https://osf.io/zxfmy/files/osfstorage
       wget https://osf.io/download/4yv85/ -O file_list.all.latest.tsv.gz

   If you only need to add assemblies from an incremental version,
   please manually download the file list `here <https://osf.io/zxfmy/files/osfstorage>`__.

2. Downloading assembly tarball files.

   ::

       # Tarball file names and their URLs
       zcat file_list.all.latest.tsv.gz | awk 'NR>1 {print $3"\t"$4}' | uniq > tar2url.tsv

       # Download. If it's interrupted, just rerun the same command.
       cat tar2url.tsv | rush --eta -j 2 -c -C download.rush 'wget -O {1} {2}'

3. Decompressing all tarballs. The decompressed genomes are stored in
   plain text, so we use ``gzip`` (can be replaced with faster ``pigz``)
   to compress them to save disk space.

   ::

       # {^tar.xz} is for removing the suffix "tar.xz"
       ls *.tar.xz | rush --eta -c -C decompress.rush 'tar -Jxf {}; gzip -f {^.tar.xz}/*.fa'

       cd ..

   After that, the assemblies directory would have multiple
   subdirectories. When you give the directory to ``lexicmap index -I``,
   it can recursively scan (plain or gz/xz/zstd-compressed) genome
   files. You can also give a file list with selected assemblies.

   ::

       $ tree atb | more
       atb
       ├── atb.assembly.r0.2.batch.1
       │   ├── SAMD00013333.fa.gz
       │   ├── SAMD00049594.fa.gz
       │   ├── SAMD00195911.fa.gz
       │   ├── SAMD00195914.fa.gz

4. Prepare a file list of assemblies.

   -  Just use ``find`` or `fd <https://github.com/sharkdp/fd>`__ (much
      faster).

      ::

          # find
          find atb/ -name "*.fa.gz" > files.txt

          # fd
          fd .fa.gz$ atb/ > files.txt

      What it looks like:

      ::

          $ head -n 2 files.txt
          atb/atb.assembly.r0.2.batch.1/SAMD00013333.fa.gz
          atb/atb.assembly.r0.2.batch.1/SAMD00049594.fa.gz

   -  (Optional) Only keep assemblies of high-quality.
      Please `click this link <https://osf.io/download/m26zn/>`_ to
      download the ``hq_set.sample_list.txt.gz`` file, or from this
      `page <https://osf.io/h7wzy/files/osfstorage/>`_.

      ::

          find atb/ -name "*.fa.gz" | grep -w -f <(zcat hq_set.sample_list.txt.gz) > files.txt

5. Creating a LexicMap index (`tutorials <https://bioinf.shenwei.me/LexicMap/tutorials/index/>`__).
   It took 47h40m and 145GB RAM with 48 CPUs for 2.44 million ATB genomes.

   ::

       lexicmap index -S -X files.txt -O atb.lmi -b 25000 --log atb.lmi.log

       # dirsize atb.lmi
       atb.lmi: 5.24 TiB (5,758,875,365,595)
         2.87 TiB      seeds
         2.37 TiB      genomes
        51.70 MiB      genomes.map.bin
       156.28 KiB      masks.bin
        61.02 KiB      genomes.chunks.bin
            619 B      info.toml

6. Searching with LexicMap (`tutorial <https://bioinf.shenwei.me/LexicMap/tutorials/search/>`__).
