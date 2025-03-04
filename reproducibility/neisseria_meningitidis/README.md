*Neisseria meningitidis* - Typing
===============================
MLST, serotyping, finetyping, Bexsero, MenDeVAR
-----------------------------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Neisseria meningitidis* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [meningotype](https://github.com/MDU-PHL/meningotype), which returns [serotype](https://pubmed.ncbi.nlm.nih.gov/14715772/), MLST, [Finetyping](https://pubmed.ncbi.nlm.nih.gov/17168996/), [Bexsero antigen typing](https://pmc.ncbi.nlm.nih.gov/articles/PMC5012890/), and [MenDeVAR (Meningococcal Deduced Vaccine Antigen Reactivity) Index](https://pubmed.ncbi.nlm.nih.gov/33055180/)

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [meningotype](https://github.com/MDU-PHL/meningotype) v0.8.5
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# Kleborate
Generate a list of all of the *Neisseria meningitidis* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-nmen-genomes.txt
```

Use ``GNU parallel`` to run ``meningotype``
```bash
mkdir meningotype

parallel --jobs 16 --colsep "\t" 'meningotype --all {2} 2> /dev/null > ./meningotype/{1}.tsv' :::: atb-nmen-genomes.txt
```

Use ``csvtk`` to merge all the ``meningotype`` results
```bash
find $PWD/meningotype/ -name "*.tsv" > meningotype-result-list.txt

csvtk concat --keep-unmatched --unmatched-repl "NA" --tabs --out-tabs --num-cpus 16 --lazy-quotes --infile-list meningotype-result-list.txt | awk -F"\t" -v OFS="\t" '{if (NR>1) { i = split($1,p,"/"); $1=p[i]; gsub(".fa","",$1) }; print}' | csvtk sort --tabs --out-tabs --keys "SAMPLE_ID" > atb0.2-nmen-meningotype-v0.8.5-merged.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Neisseria meningitidis* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
