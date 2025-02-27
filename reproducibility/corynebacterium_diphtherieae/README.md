*Corynebacterium diphtherieae* - Typing
=====================================
MLST and toxin
--------------

All [sylph](https://github.com/bluenote-1577/sylph)-identified *Corynebacterium diphtherieae* genomes from [AllTheBacteria](https://allthebacteria.readthedocs.io/en/latest/) ``0.2`` and ``incremental release 2024-08`` were typed using [multi locus sequencing typing (MLST)](https://github.com/tseemann/mlst) and for the diphtheriae toxin

# Tools used
* [csvtk](https://github.com/shenwei356/csvtk) v0.30.0
* [seqkit](https://github.com/shenwei356/seqkit) v2.8.2
* [mlst](https://github.com/tseemann/mlst) v2.23.0 and [diphtheria_3](http://www.pubmlst.org) schema downloaded 2024-06-10
* [blastn](https://pubmed.ncbi.nlm.nih.gov/2231712/) 2.15.0+
* [GNU parallel](https://www.gnu.org/software/parallel/) 20240522

# MLST
Generate a list of all of the *Corynebacterium diphtherieae* genomes

```bash
for x in $(find $PWD -name "*.fa"); do echo -e $(basename "$x" .fa)"\t"$x; done > atb-cdiph-genomes.txt
```

Use ``GNU parallel`` to run ``mlst``

```bash 
parallel --jobs 16 --colsep "\t" 'mlst --quiet --label {1} --scheme diphtheria_3 {2}' :::: atb-cdiph-genomes.txt | sort > atb0.2-cdiphtheriae-mlst.tsv
```

# Toxin profiling
Use ``blastn`` against the diptheriae toxin [DIP_RS12515](https://www.ncbi.nlm.nih.gov/gene/2650491) from [NC_002935.2](https://www.ncbi.nlm.nih.gov/nuccore/NC_002935.2), keeping ``bitscores > 2000``

```bash
for x in $(ls corynebacterium_diphtheriae__01/*.fa)
do
	blastn -outfmt '6 std sseq' -query DIP_RS12515.fna -subject $x \
		| awk -F"\t" -v OFS="\t" -v genome=$(basename "$x" .fa) '$12>2000{print genome,$0}' \
		| sort -nrk13
done > blastn-seed.tsv
```

Use seqkit to translate ``column 14`` following gap removal, and capture the ``amino-acid sequence``.<br>
Type the toxin sequence against the [tox.fas](https://gitlab.pasteur.fr/BEBP/diphtoscan/-/tree/main/data/tox/sequences) sequences from [dipthOscan](https://peercommunityjournal.org/articles/10.24072/pcjournal.307/)

```bash
while read a b c d e f g h i j k l m n
do
	# use seqkit to translate column 14 (variable n), after removing gaps
	translate=$(seqkit seq --remove-gaps <(echo -e ">x\n"${n}) | seqkit translate --trim --line-width 0 | tail -1)
	
	# take the best blastn bitscore of the sequence (column 14) against the diphtOscan tox.fas typing sequences
	toxtype=$(blastn -outfmt 6 -query tox.fas -subject <(seqkit seq --remove-gaps <(echo -e ">x\n"${n})) | sort -nrk12 | head -1 | cut -f1,3 | awk -F"\t" '{print $1":"$2}')
	
	printf '%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n' "$a" "$b" "$c" "$d" "$e" "$f" "$g" "$h" "$i" "$j" "$k" "$l" "$m" "$n" "$translate" "${#translate}" "$toxtype"
	
done < blastn-seed.tsv \
	| csvtk add-header --tabs --out-tabs --names "sequence-id,qseqid,sseqid,pident,length,mismatch,gapopen,qstart,qend,sstart,send,evalue,bitscore,qseq,translated-qseq,aa-length,toxtype:percent-identity" > atb0.2-cdiphtheriae-toxins.tsv
```

Clean up
```bash 
rm blastn-seed.tsv
```

The same commands, software and database versions were used for ``incremental release 2024-08`` genomes except different output filenames were generated.

For any questions regarding the *Corynebacterium diphtherieae* typing, please contact [Matthew Croxen](mailto:mcroxen@ualberta.ca).
