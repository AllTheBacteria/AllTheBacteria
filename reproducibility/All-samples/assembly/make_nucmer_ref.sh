#!/usr/bin/env bash
wget https://github.com/ANHIG/IMGTHLA/archive/refs/tags/v3.55.0-alpha.zip
unzip v3.55.0-alpha.zip
wget https://ftp.ncbi.nlm.nih.gov/genomes/all/GCA/009/914/755/GCA_009914755.4_T2T-CHM13v2.0/GCA_009914755.4_T2T-CHM13v2.0_genomic.fna.gz
mkdir GCA_009914755.split_ref
fastaq split_by_base_count GCA_009914755.4_T2T-CHM13v2.0_genomic.fna.gz GCA_009914755.split_ref/ref 200000000
cp IMGTHLA-3.55.0-alpha/hla_gen.fasta GCA_009914755.split_ref/
