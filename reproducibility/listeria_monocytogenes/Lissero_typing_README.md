Listeria monocytogenes serotyping (LisSero)

Tool: LisSero 

Database: LisSero DB

Github: https://github.com/MDU-PHL/LisSero

Environment: see file lissero_env.txt 

Command run: 

```bash
cat Listeria_mono.tab | parallel -j 20 --colsep '\t' 'lissero /home/shared/db/all-the-bacteria/batch/{3} --min_id 95 --min_cov 95  > lissero/{1}_lissero'
```

Notes on command run: Listeria_mono.tab is a subsetted list from master assembly based on sylph id. 

OSF project ID code: [https://osf.io/9cbqg](https://osf.io/9cbqg/)
Manuscripts: PMID: [15297538](https://pubmed.ncbi.nlm.nih.gov/15297538/);