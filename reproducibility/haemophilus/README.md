*Haemophilus* spp. - Typing
=========================
MLST and capsule
----------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Haemophilus* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [multi locus sequencing typing (MLST)](https://github.com/tseemann/mlst) and [hicap](https://pubmed.ncbi.nlm.nih.gov/30944197/) for capsule typing.

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [haemophilus](http://www.pubmlst.org) schema downloaded 2024-06-10
* [hicap](https://pubmed.ncbi.nlm.nih.gov/30944197/) v1.0.4
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# MLST
Generate a list of all of the *Haemophilus* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-haemophilus-genomes.txt
```

Use ``GNU parallel`` to run ``mlst``
```bash 
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme hinfluenzae {2}' :::: atb-haemophilus-genomes.txt | sort > atb0.2-haemophilus-mlst.tsv
```

# Capsule typing (hicap)
Use ``GNU parallel`` to run ``hicap``
```bash
parallel --jobs 16 --colsep "\t" 'hicap --query_fp {2} --output_dir hicap' :::: atb-haemophilus-genomes.txt
```

Use ``csvtk`` to merge all the ``hicap`` results
```bash
find $PWD/hicap/ -name "*.tsv" > hicap-result-list.txt

csvtk concat --keep-unmatched --unmatched-repl "NA" --tabs --out-tabs --num-cpus 16 --lazy-quotes --comment-char '$' --infile-list hicap-result-list.txt | csvtk sort --tabs --out-tabs --keys "#isolate" --comment-char '$' > atb0.2-haemophilus-hicap-v1.0.4-merged.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Haemophilus* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
