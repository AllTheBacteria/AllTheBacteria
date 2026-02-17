Multi-locus sequence typing - All samples  (MLST)

Tool: MLST, MLSTDB 

Database: pubMLST and pasteurMLST databases for all schemes available, provided in mlst_schemes.txt including date of last update for that scheme.

Github: https://github.com/tseemann/mlst; https://github.com/MDU-PHL/mlstdb 

Environment: see file mlst-atb_env.txt 

Command run: 

```bash
cat batch.tsv | parallel -j 175 --colsep '\t' 'mlst --quiet --full --blastdb /home/shared/db/mlst/db_all_schemes_v20260203/blast/mlst.fa --datadir /home/shared/db/mlst/db_all_schemes_v20260203/pubmlst /home/shared/db/all-the-bacteria/batch/{4} > mlst/{1}.mlst' 
```

Notes on command run: mlst does auto-detecion of best fit scheme for typing. for several genomes two perfect schemes were matched and other non were matched, however by default only one scheme is printed out. three schmemes were selected to be excluded as they are known to the not maintained. 

```bash
--exclude [X]     Ignore these schemes (comma sep. list) (default 'ecoli,abaumannii,vcholerae_2')
```
There needs to be further work on this to attempt to separate these cases and determine which scheme was most apporpirate to be used. ideally we would provide a aditional list of suspect schemes;profiles;alleles. Rerunning samples to track stderr outputs to list all conflicting genome entries 

OSF project ID code: [https://osf.io/23hx6](https://osf.io/23hx6/files/osfstorage)
Manuscripts/PMID: PMID: 30345391