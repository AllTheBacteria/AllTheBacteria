*Streptococcus pyogenes* (GAS) - Typing
=====================================
MLST, emm, M1UK, M1DK
---------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Streptococcus pyogenes* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [mlst](https://github.com/tseemann/mlst), [emm-typer](https://github.com/MDU-PHL/emmtyper) and [assembly_typer](https://github.com/boasvdp/assembly_snptyper) ([M1UK](https://pubmed.ncbi.nlm.nih.gov/31519541/), [M1DK](https://pubmed.ncbi.nlm.nih.gov/38961826/))

# Tools used
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [spyogenes](www.pubmlst.org) schema (downloaded 2024-06-10)
* [emm-typer](https://github.com/MDU-PHL/emmtyper) v0.2.0
* [assembly_typer](https://github.com/boasvdp/assembly_snptyper) v0.1.0 ([M1UK](https://pubmed.ncbi.nlm.nih.gov/31519541/), [M1DK](https://pubmed.ncbi.nlm.nih.gov/38961826/))
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522
* [samtools](https://pubmed.ncbi.nlm.nih.gov/19505943/) 1.19.2
* [pandas](https://pandas.pydata.org/) 2.2.2
* [minimap2](https://pubmed.ncbi.nlm.nih.gov/29750242/) 2.28

# MLST
Generate a list of all of the *Streptococcus pyogenes* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-gas-genomes.txt
```

Use ``GNU parallel`` to run ``mlst``
```bash
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme spyogenes {2}' :::: atb-gas-genomes.txt | sort > atb0.2-gas-mlst.tsv
```

# emm typing
Use ``GNU parallel`` to run ``emmtyper``
```bash
parallel --jobs 16 --colsep "\t" 'emmtyper --workflow blast {2} --output-format verbose 2> /dev/null' :::: atb-gas-genomes.txt | awk -F"\t" -v OFS="\t" '{gsub(".tmp","",$1); print}' | sort > atb0.2-gas-emmtyper.tsv
```

# Typing EMM1.x for M1UK and M1DK 

Get a list of the EMM1.x genomes
```bash
awk -F"\t" '{if (FNR==NR && $4~"EMM1\\.") { emm1[$1]="1" } else { if (emm1[$1]) { print $2 } }}' atb0.2-gas-emmtyper.tsv atb-gas-genomes.txt > atb-gas-emm1-genomes.txt
```

Use ``assembly_snptyper`` to assess EMM1 emm-types as M1UK or M1DK
```bash
for vcf in {M1UK,M1DK}
do 
	assembly_snptyper --processes 16 --vcf ./assembly_snptyper/data/"${vcf}".vcf --reference ./assembly_snptyper/data/MGAS5005.fa --list_input atb-gas-emm1-genomes.txt > atb0.2-gas-"${vcf}".tsv
done
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Streptococcus pyogenes* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
