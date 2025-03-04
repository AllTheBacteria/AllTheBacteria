*Streptococcus agalactiae* (GBS) - Typing
=======================================
MLST, capsule
-------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Streptococcus agalactiae* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [mlst](https://github.com/tseemann/mlst) and [GBS-SBG](https://pubmed.ncbi.nlm.nih.gov/34895403/)

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [sagalactiae](www.pubmlst.org) schema (downloaded 2024-06-10)
* [GBS-SBG](https://pubmed.ncbi.nlm.nih.gov/34895403/) (git commit 9e53847)
* [blastn](https://pubmed.ncbi.nlm.nih.gov/2231712/) 2.14.1+
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# MLST
Generate a list of all of the *Streptococcus agalactiae* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-gbs-genomes.txt
```

Use ``GNU parallel`` to run ``mlst``
```bash
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme sagalactiae {2}' :::: atb-gbs-genomes.txt | sort > atb0.2-gbs-mlst.tsv
```

Use ``GNU parallel`` to run ``GBS-SBG``
```bash
parallel --jobs 16 --colsep "\t" "GBS-SBG.pl -ref GBS-SBG.fasta -best {2}" :::: atb-gbs-genomes.txt | awk -F"\t" -v OFS="\t" '$1!="# Name" {gsub(".fa","",$1); print}' | sort > atb0.2-gbs-GBS-SBG.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Streptococcus agalactiae* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
