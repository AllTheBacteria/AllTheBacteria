# Assembly stats

The final output file of assembly statistics is available here:
https://osf.io/h7g42.

Version of `assembly-stats` used: git commit 7bdb58b from
https://github.com/sanger-pathogens/assembly-stats

The main script is `assembly_stats_batch.py`, which runs `assembly-stats`
on a batch of assemblies, outputting a single TSV file of results.

The whole process was run as follows on the EBI compute slurm cluster.
If you want to run yourself, then you will need to fix the hard-coded
paths. Look for `FIX_ME` in the python script.

The script has a hard-coded path to a TSV file that looked like this:
```
$ head -n3 sample_path.tsv
Sample  Path
SAMD00075885    1300k/batch_68/ilmn-SAMD00075885_contigs.fa.gz
SAMN16231665    1300k/batch_68/ilmn-SAMN16231665_contigs.fa.gz
```
It had 1943494 lines.

The SLURM jobs were submitted with:

```
mkdir Splits
seq 1 10000 1943494 | awk '{s="slurmzy run 0.2 Splits/stats."$1" ./assembly_stats_batch.py "$1" "($1+9999)" Splits/stats."$1".tsv"; print s; system(s)}'
```

Note: `surmzy` can be obtained from https://github.com/martinghunt/slurmzy.
It's a wrapper for running `srun`.

There was an off-by-one error meaning that the first sample needed to be
run manually. And then gather all the results into one file:

```
assembly-stats -t /FIX_PATH/ilmn-SAMD00075885_contigs.fa.gz | awk 'NR>1 {OFS="\t"; $1="SAMD00075885"} 1' | sed 's/filename/sample/'  > assembly-stats.tsv
for x in `seq 1 10000 1943494 `; do awk 'NR>1' Splits/stats.$x.tsv >> assembly-stats.tsv ; done
```
