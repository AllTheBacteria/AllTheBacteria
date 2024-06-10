# checkm2

Version of checkm2: 1.0.1. The singularity container used is here:
https://osf.io/7vpy3

Checkm2 database: uniref100.KO.1.dmnd. A copy of this is here:
https://osf.io/x5vtj


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

