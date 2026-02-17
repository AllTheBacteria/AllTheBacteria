**Vibrio parahaemolytics serotyping (Kaptive3)** 
Tool : Kaptive3 

Database:  Vp_O and Vp_K database from PMID: 37130055

Github/Web: https://kaptive.readthedocs.io/en/latest/  and https://github.com/aldertzomer/vibrio_parahaemolyticus_genomoserotyping

Environment: see file kaptive3_env.txt 

Commands run: 

```bash
cat V_para_ATB.tab | parallel -j 20 --colsep '\t' 'kaptive assembly /kaptive_db/vibrio_parahaemolyticus_genomoserotyping/VibrioPara_Kaptivedb_O.gbk  /home/shared/db/all-the-bacteria/batch/{3} -o kaptive/{1}_kaptive_Vp_k.tsv 
```

```bash
cat V_para_ATB.tab | parallel -j 20 --colsep '\t' 'kaptive assembly /kaptive_db/vibrio_parahaemolyticus_genomoserotyping/VibrioPara_Kaptivedb_O.gbk /home/shared/db/all-the-bacteria/batch/{3} -o kaptive/{1}_kaptive_Vp_O.tsv
```

Notes on commands run: V_para_ATB.tab input file is a subsetted list from master assembly based on sylph id. 
OSF project ID code:  https://osf.io/xc26j 
Manuscripts/PMID: PMID: 40553506; PMID: 37130055