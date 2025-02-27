*Mycobacterium tuberculosis* - Typing
===================================
Spoligotyping, lineage, antimicrobial resistance
------------------------------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Mycobacterium tuberculosis* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed (spoligotype, lineage, antimicrobial resistance) using [TBProfiler](https://pubmed.ncbi.nlm.nih.gov/31234910/)

# Tools used
* [TBProfiler](https://pubmed.ncbi.nlm.nih.gov/31234910/) v6.2.1
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# TBProfiler
Generate a list of all of the *Mycobacterium tuberculosis* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-mtb-genome-list.txt
```

Use ``GNU parallel`` to run ``TBProfiler``
```bash
parallel --jobs 60 --colsep "\t" 'tb-profiler profile -f {2} --prefix {1} --spoligotype' :::: atb-mtb-genome-list.txt
```

Collate the data
```bash
tb-profiler collate
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Mycobacterium tuberculosis* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
