**Acinetobacter baumannii serotyping (Kaptive3)** 

Tool: Kaptive3 

Database: Ab_O and Ab_K within Kaptive3 

Github/Web: https://kaptive.readthedocs.io/en/latest/ 

Environment: see file kaptive3_env.txt 

Commands run: 

```bash
cat acinetobacter_b_ATB.tab | parallel -j 20 --colsep '\t' 'kaptive assembly ab_k /home/shared/db/all-the-bacteria/batch/{3} -o kaptive/{1}_kaptive_Ab_k.tsv
```

```bash
cat acinetobacter_b_ATB.tab | parallel -j 20 --colsep '\t' 'kaptive assembly ab_o /home/shared/db/all-the-bacteria/batch/{3} -o kaptive/{1}_kaptive_Ab_O.tsv
```

Notes on commands run: acinetobacter_b_ATB is a subsetted list from master assembly based on sylph id. 

OSF project ID code: https://osf.io/vjma7 
Manuscripts/PMID:  PMID: 32118530, PMID: 36214673; PMID: 40553506