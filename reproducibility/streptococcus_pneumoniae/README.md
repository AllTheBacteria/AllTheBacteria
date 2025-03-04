*Streptococcus pneumoniae* - Typing
=================================
MLST, capsule
-------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Streptococcus pneumoniae* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [mlst](https://github.com/tseemann/mlst) and [PneumoKITy](https://pmc.ncbi.nlm.nih.gov/articles/PMC9837567/)

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [spneumoniae](www.pubmlst.org) schema (downloaded 2024-06-10)
* [PneumoKITy](https://pmc.ncbi.nlm.nih.gov/articles/PMC9837567/) v1.0 (capsule)
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522
* [mash](https://pmc.ncbi.nlm.nih.gov/articles/PMC4915045/) v2.3
* [numpy](https://pubmed.ncbi.nlm.nih.gov/32939066/) v1.26.4
* [pandas](https://pandas.pydata.org/) v2.2.0
* [sqlalchemy](https://www.sqlalchemy.org/) v2.0.27
* [python](https://www.python.org/) v3.12.1
* [perl](https://www.perl.org/) v5.32.1

# MLST
Generate a list of all of the *Streptococcus pneumoniae* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-spneumoniae-genomes.txt
```

Use ``GNU parallel`` to run ``mlst``
```bash
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme spneumoniae {2}' :::: atb-spneumoniae-genomes.txt | sort > atb0.2-spneumoniae-mlst.tsv
```
# Serotyping

Use ``GNU parallel`` to run ``PneumoKITy``
```bash
mkdir pneumokity-results

parallel --jobs 16 --colsep "\t" 'python pneumokity.py pure --threads 1 --sampleid {1} --assembly {2} --output_dir pneumokity-results' :::: atb-spneumoniae-genomes.txt
```

Use ``csvtk`` to merge the ``PneumoKITy`` results
```bash
find $PWD/pneumokity-results/pneumo_capsular_typing/ -name "*_result_data.*" > pneumokity-result-list.txt

csvtk concat --keep-unmatched --unmatched-repl "NA" --out-tabs --num-cpus 16 --lazy-quotes --infile-list pneumokity-result-list.txt | csvtk sort --tabs --out-tabs --keys "sampleid" > atb0.2-pneumokity.v1.0-merged.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Streptococcus pneumoniae* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
