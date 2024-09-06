wget https://github.com/shenwei356/gtdb-taxdump/releases/download/v0.4.0/gtdb-taxdump.tar.gz
tar -zxvf gtdb-taxdump.tar.gz
cp -r gtdb-taxdump/R214 taxdump

cat taxdump/taxid.map \
    | taxonkit --data-dir taxdump/ reformat -I 2 -f '{s}' \
    | csvtk cut -Ht -f 1,3 \
    | csvtk replace -Ht -p $ -r .fna.gz \
    > gtdb_r214.syldb.file2species.map
