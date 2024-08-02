# checkm2

Version of checkm2: 1.0.1. The singularity container used is here:
https://osf.io/7vpy3 and the download URL is https://osf.io/download/7vpy3/.
Example `wget` command:
```
wget -O checkm2.1.0.1--pyh7cba7a3_0.img https://osf.io/download/7vpy3/
```

Checkm2 database: uniref100.KO.1.dmnd. A copy of this is here:
https://osf.io/x5vtj and the download URL is https://osf.io/download/x5vtj/.
Example `wget` command:
```
wget -O uniref100.KO.1.dmnd  https://osf.io/download/x5vtj/
```

This was all run on the EBI SLURM compute cluster. Some paths
were hard-coded. You will need to change them to run on your own
data. Look for `FIX_PATH` in the python script.

A SLURM job array was used, which was submitted using
```
sbatch checkm2.sbatch
```
Each element of the array ran a batch of samples in serial using the
script `checkm2_batch.py`. See inside that script for notes on what would
need changing if you want to run this script yourself.

