*Bordetella pertussis* - Typing
=============================
MLST and BPagST (antigen)
-------------------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Bordetella pertussis* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [multi locus sequencing typing (MLST)](https://github.com/tseemann/mlst) and [BPagST](https://pubmed.ncbi.nlm.nih.gov/35778384/)

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [seqkit](https://github.com/shenwei356/seqkit) v2.8.2
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [bordtella_3](www.pubmlst.org) schema (downloaded 2024-06-10)
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522 

# BPagST schema
Download the BPagST alleles from [BIGSdb Institut Pasteur](https://bigsdb.pasteur.fr/cgi-bin/bigsdb/bigsdb.pl?db=pubmlst_bordetella_seqdef&page=schemeInfo&scheme_id=7) add to ``mlst`` (commands worked as of ``2024-06-10``)

| Locus | Alleles | Aliases | Last updated |
|-------|---------|---------|--------------|
| ptxP	| 40	| | 2021-05-11 |
| ptxA (BP3783) | 44 | BP3783; BP_RS19040; ptxS1 | 2024-02-29 |
| ptxB (BP3784)	| 26 | ptxS2 | 2022-06-16 |
| ptxC		| 25 | BP3787; ptxS3 | 2024-02-29 |
| ptxD (BP3785) | 26 | ptxS4 | 2022-06-16 |
| ptxE (BP3786)	| 21 | ptxS5 | 2024-03-05 |
| fhaB-2400_5550 | 100 | 			| 2021-07-22 |
| fim2 (BP1119)	| 17 | BP1119; BP_RS05570 | 2024-03-05 |
| fim3 (BP1568)	| 45 | BP1568; BP_RS07840 | 2024-01-12 |

Download the schema from [BIGSdb Institut Pasteur](https://bigsdb.pasteur.fr/cgi-bin/bigsdb/bigsdb.pl?db=pubmlst_bordetella_seqdef&page=schemeInfo&scheme_id=7)
```bash 
wget "https://bigsdb.pasteur.fr/cgi-bin/bigsdb/bigsdb.pl?db=pubmlst_bordetella_seqdef&page=downloadProfiles&scheme_id=7" --output-document BPagST-scheme.txt
```

Use ``csvtk`` to rename alleles in ``BPagST-scheme.txt`` to be compatible with ``mlst``
```bash 
csvtk rename --tabs --out-tabs --fields 'BPagST,fhaB-2400_5550' --names 'ST,fhaB' BPagST-scheme.txt > BPagST.txt
```

Download each allele from [BIGSdb Institut Pasteur](https://bigsdb.pasteur.fr/cgi-bin/bigsdb/bigsdb.pl?db=pubmlst_bordetella_seqdef&page=schemeInfo&scheme_id=7)
```bash
for allele in {ptxP,ptxA,ptxB,ptxC,ptxD,ptxE,fhaB-2400_5550,fim2,fim3}
do 
	wget "https://bigsdb.pasteur.fr/cgi-bin/bigsdb/bigsdb.pl?db=pubmlst_bordetella_seqdef&page=downloadAlleles&locus=""${allele}" --output-document "${allele}".tfa
done
```

Use ``seqkit`` to rename the fhaB alleles to be ``mlst`` compatible
```bash
seqkit replace --pattern "\-2400_5550" --replacement '' fhaB-2400_5550.tfa > fhaB.tfa
```

Copy the data to ``mlst`` and make the ``blast database`` again
```bash
mkdir /home/user/miniforge3/envs/mlst/db/pubmlst/BPagST/

mv BPagST.txt /home/user/miniforge3/envs/mlst/db/pubmlst/BPagST/

for a in {ptxP,ptxA,ptxB,ptxC,ptxD,ptxE,fhaB,fim2,fim3}; do mv ${a}.tfa /home/user/miniforge3/envs/mlst/db/pubmlst/BPagST/; done

mlst-make_blast_db
```

# Typing
Generate a list of all of the *Bordetella pertussis* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x done > atb-bordetella-genomes.txt
```

Use ``GNU parallel`` to run tradtional ``mlst`` and the ``BPagST`` scheme

```bash 
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme BPagST {2}' :::: atb-bordetella-genomes.txt | sort > atb0.2-bordetella-BPagST.tsv
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme bordetella_3 {2}' :::: atb-bordetella-genomes.txt | sort > atb0.2-bordetella-mlst.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Bordetella pertussis* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
