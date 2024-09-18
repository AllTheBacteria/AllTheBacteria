# Miniphy

## Incremental release 202408

These are notes from compressing the incremental release 2024-08 with Miniphy,
run on the EBI SLURM cluster. Internal paths have been removed -- to run
yourself you would need to fix some paths.

### Prepare files

We have the assembly of each sample in its own FASTA file. The file list
looks like this:

```
$ zcat file_list.incr.202408.tsv.gz | head
Sample	Path
SAMD00046204	Assemblies/20240625/batch.1/SAMD00046204.fa.gz
SAMD00046205	Assemblies/20240625/batch.1/SAMD00046205.fa.gz
```

Using the `species_calls.tsv.gz` file for the release, make a sorted file
to species TSV file to use later with miniphy.

```
zcat file_list.incr.202408.tsv.gz | sed 1d | csvtk replace -Ht -f 2 -p ^ -r /path/to/projects/AllTheBacteria/ -o file_list.txt

zcat /path/to/species_calls.tsv.gz  | sed 1d > sample2species.tsv

csvtk sort -Ht -k 1:N file_list.txt \
    | csvtk replace -Ht -f 1 -p '(.+)' -r '{kv}' -k sample2species.tsv \
    | csvtk cut -Ht -f 2,1 \
    | csvtk add-header -t -n file,species \
    > file2species.sorted.tsv
```

The files made look like this:
```
$ head -n3 file_list.txt
SAMD00046204	/path/to/Assemblies/20240625/batch.1/SAMD00046204.fa.gz
SAMD00046205	/path/to/Assemblies/20240625/batch.1/SAMD00046205.fa.gz
SAMD00046206	/path/to/Assemblies/20240625/batch.1/SAMD00046206.fa.gz
$ head -n3 sample2species.tsv
SAMD00046204	Streptococcus pyogenes
SAMD00046205	Streptococcus pyogenes
SAMD00046206	Streptococcus pyogenes
$ head -n3 file2species.sorted.tsv
file	species
/nfs/research/zi/projects/AllTheBacteria/Assemblies/20240625/batch.1/SAMD00046204.fa.gz	Streptococcus pyogenes
/nfs/research/zi/projects/AllTheBacteria/Assemblies/20240625/batch.1/SAMD00046205.fa.gz	Streptococcus pyogenes
```



### Set up conda

See https://github.com/karel-brinda/MiniPhy.

```
conda create -n miniphy python=3.7
conda activate miniphy
```

Note: have to remove `-c default` from this command because we can't use it any more.
EBI blocks it.

```
conda install -c conda-forge -c bioconda make "python>=3.7" "snakemake-minimal>=6.2.0" "mamba>=0.20.0"
```

Need this for `./create_batches.py` later:
```
python3 -m pip install xopen
```

And this for running make in each copy of miniphy repo:
```
python3 -m pip install ete3
```

Clone:
```
git clone https://github.com/karel-brinda/miniphy
```


### Create batches
```
cd miniphy/
```

```
$ ./create_batches.py ../file2species.sorted.tsv -d input/ -s species -f file -c -m 200
Loaded 507564 genomes across 3749 species clusters
Put 27056 genomes of 3653 species into the dustbin
Created 223 batches of 97 pseudoclusters
Finished
```

```
cd ..
cp -r miniphy/input batches/
```

### Setup copies of miniphy

Sort files by size:
```
ls -S batches/* | grep txt > batches.txt
```

`batches.txt` looks like this:
```
$ head -n3 batches.txt
batches/mycobacterium_tuberculosis__03.txt
batches/mycobacterium_tuberculosis__02.txt
batches/mycobacterium_tuberculosis__04.txt
```

Split into `$n` chunks using round robin distribution:
```
n=66
split -n r/$n -d  batches.txt batches.n-


ls -d batches.n-* | grep -v miniphy \
    | rush -j 5 --eta 'cp -r miniphy/ {}.miniphy; rm {}.miniphy/input/*; \
        cat {} | while read f; do cp $f {}.miniphy/input/; done;' \
        -c -C copy.rush
```

Need to remove all mentions of conda default, because we can't use it.
Jellyfish doesn't have conda-forge. The rest do.
Fix jellyfish first, then remove all defaults:
```
find . -name jellyfish.yaml | xargs sed -i 's/defaults/conda-forge/'
find . -name "*.yaml" | grep envs | xargs sed -i '/defaults/d'
```

Install conda envs for all copies.
You can't `make test` for one repo and copy it N times. You have to run on
all copies.
```
slurmzy run 1 make_all_the_thingz 'source ~/.bashrc && conda activate miniphy && for x in *.miniphy; do echo "--------------- $x ------------" && cd $x && make test && cd .. ; done'
```


### Run miniphy

```
ls -d batches.n-*.miniphy | rush 'slurmzy run -t 24 -c 8 50 {} "source ~/.bashrc; cd {}; conda activate miniphy; make clean; make all"'
```


### Rename tarballs

We rename all the tarballs afterwards to remove species names.
One slurm job per tarball:

```
mkdir /path/to/OUTDIR
ls batches.*.miniphy/output/asm/*.tar.xz | sort -t/ -k4 | awk 'BEGIN{o="/path/to/OUTDIR"} {n="atb.assembly.incr_release.202408.batch."NR; s="slurmzy run 1 "o"/"n" ./remake_tarball.pl "$1" "o" "n ; print s; system(s)}'
```

The script `remake_tarball.pl` is included in this repository in the same folder
as this README file.
