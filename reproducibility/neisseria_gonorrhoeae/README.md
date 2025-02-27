*Neisseria gonorrhoeae* - Typing
==============================
MLST, NG-MAST, NG-STAR, *penA*
----------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Klebsiella* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [pyngoST](https://pubmed.ncbi.nlm.nih.gov/38288762/) which return MLST, [*N. gonorrhoeae* multi-antigen sequence typing (NG-MAST)](https://pubmed.ncbi.nlm.nih.gov/15073688/), [*N. gonorrhoeae* sequence typing for antimicrobial resistance (NG-STAR)](https://pubmed.ncbi.nlm.nih.gov/28228492/), and *penA* results.

# Tools used
* [pyngoST](https://pubmed.ncbi.nlm.nih.gov/38288762/) v1.1.2 (CC database 240513_NGSTAR_CC_updated)
* [muscle](https://drive5.com/muscle/downloads_v3.htm) 3.8.1551

# pyngoST
Generate a list of all of the *Klebsiella* genomes

```bash
# Despite it saying it can handle .fa, it only wants .fasta - so create symlinks
mkdir symlink

for x in $(find $PWD -name "*.fa"); do ln -s $x $PWD/symlink/$(basename $x .fa).fasta; done

find $PWD/symlink -name "*.fasta" > input-for-pyngost.txt
```

Run ``pyngoST``
```bash
# note there is a bug that won't play nice with Muscle and thus the genogroups cannot be calculated (--genogroups)
pyngoST.py --read_file input-for-pyngost.txt --path $PWD/allelesDB/ --schemes MLST,NG-MAST,NG-STAR --ngstarccs --mosaic_pena --num_threads 60 --out_filename atb-ngo-pyngost-results.tsv
```
#### inc-rel-2024-08 comment
SAMN41637290 does not appear to be a *N. gonorrhoeae*: nearest match in [GTDB](https://pubmed.ncbi.nlm.nih.gov/34520557/) looks to be s__Pseudomonas_E sp000955815

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Neisseria gonorrhoeae* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
