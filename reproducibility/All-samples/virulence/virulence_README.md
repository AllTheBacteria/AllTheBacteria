Virulence Factor Screening - All samples  (Abricate with VFDB)

Tool: Abricate 

Database: VFDB2024 (https://www.mgc.ac.cn/VFs/) 

Github: https://github.com/tseemann/abricate

Environment: see file abricate_env.txt 

Command run: 

```bash
cat batch.tsv | parallel -j 100 --colsep '\t' 'abricate /home/shared/db/all-the-bacteria/batch/{4} --db vfdb --minid 80 --mincov 80 > vfdb/{1}.t

```

Notes on command run: abricate was run with 80% identity and 80% coverage. output file was generated and summarised for each sample including those with no gene hits. abricate also only screens based on nucleotide sequence not amino acid (this may change in the future)  

OSF project ID code: https://osf.io/8mg7w
Manuscripts/PMID: PMID: 39470738; PMID: 15608208