*Legionella pneumophila* - Typing
=============================
Sequence Based Typing (SBT)
---------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Legionella pneumophila* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [legsta](https://github.com/tseemann/legsta)

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [legsta](https://github.com/tseemann/legsta) v0.5.1
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# legsta
Generate a list of all of the *Legionella pneumophila* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-legionella-genomes.txt
```

Use ``GNU parallel`` to run ``legsta``
```bash
parallel --jobs 16 --colsep "\t" 'legsta --quiet {2} > ./legsta/{1}.tsv' :::: atb-legionella-genomes.txt
```

Use ``csvtk`` to merge all the ``legsta`` results
```bash
find $PWD/legsta/ -name "*.tsv" > legsta-result-list.txt

csvtk concat --keep-unmatched --unmatched-repl "NA" --tabs --out-tabs --num-cpus 16 --lazy-quotes --infile-list legsta-result-list.txt | awk -F"\t" -v OFS="\t" '{if (NR>1) { i = split($1,p,"/"); $1=p[i]; gsub(".fa","",$1) }; print}' | csvtk sort --tabs --out-tabs --keys "FILE" > atb0.2-legionella-legsta-0.5.1-merged.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Legionella pneumophila* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
