*Klebsiella* spp. - Typing
========================
MLST, capsule, virulence, resistance
------------------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Klebsiella* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [Kleborate](https://pubmed.ncbi.nlm.nih.gov/34234121/) which returns speciation, virulence genes, MLST, capsule, and antimicrobial resistance of *Klebsiella* spp.

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [Kleborate](https://pubmed.ncbi.nlm.nih.gov/34234121/) v2.3.2
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# Kleborate
Generate a list of all of the *Klebsiella* genomes

```bash
for x in $(find $PWD/ -name "*.fa" | sort); do echo -e $(basename $x .fa)"\t"$x; done > atb-klebsiella-list.txt
```

Use ``GNU parallel`` to run ``Kleborate``
```bash
mkdir kleborate

parallel --colsep "\t" --jobs 60 'kleborate --all --assemblies {2} --outfile kleborate/{1}.kleborate.tsv' :::: atb-klebsiella-list.txt
```

Use ``csvtk`` to merge all the ``Kleborate`` results
```bash
find $PWD/kleborate/ -name "*.tsv" | sort > kleborate-output-file-list.txt

csvtk concat --keep-unmatched --unmatched-repl "NA" --tabs --out-tabs --num-cpus 60 --infile-list kleborate-output-file-list.txt > atb-0.2-kleborate.v2.3.2-merged.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Klebsiella* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
