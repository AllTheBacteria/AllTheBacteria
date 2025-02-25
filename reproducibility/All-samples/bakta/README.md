# Bakta

Genome annotations of all ATB assembled samples were conducted as a synchronized double analysis for ATB and [BakRep](https://bakrep.computational.bio/) - a web-based search & retrieval service in sync with ATB.
All original scripts used to execute Bakta on ATB assembly files are version-tagged and publicly available at https://github.com/ag-computational-bio/bakrep/tree/v2.0/nextflow. For long term storage, we additionally copied all files here and provide an extract of the relevant code at the bottom.

## Input

- `ena_metadata.tsv`: https://osf.io/ks7yt or https://ftp.ebi.ac.uk/pub/databases/AllTheBacteria/Releases/0.2/metadata/ena_metadata.tsv.gz
- Bakta version: `v1.9.4` -> https://github.com/oschwengers/bakta/releases/tag/v1.9.4, quay.io/biocontainers/bakta:1.9.4--pyhdfd78af_0
- Database version: `v5.1` -> https://doi.org/10.5281/zenodo.10522951
- Database type: `full`

## Executed command line

```bash
 nextflow run .nextflow/BakRep.nf -c ./bakrep/nextflow/nextflow.config -profile cluster --samples ena_metadata.tsv 
 --setupdir /mnt/scratch/ --data assemblies/ --results results/ -with-conda  
```

## Additional information

For the sake of file organization, BakRep internally uses different batches from ATB in order to distribute sample result files into multiple subdirectories. Different form ATB, these are not based on taxonomy but substrings of the ENA sample IDs (`batch`), for example, sample `SAMN42499475` is part of batch `N242` -> SAM **N424** 99475. However, all Bakta result files available in ATB were collected and re-distributed to match original ATB taxonomy batches.

To reduce the massive amount of annotation data, only Bakta `JSON` results files were uploaded, as they contain all available annotation information (actually more than standard file formats like `GenBank`, `EMBL` and `GFF3`). To recover those standard file formats, please use the following command that is part of Bakta:

```bash
bakta_io --output <output-path> --prefix <file-prefix> sample.json
```

## Code extract

```nextflow
nextflow.enable.dsl=2

...

        process annotation {

        tag "${sample}"
        conda "bioconda::bakta=1.9.4"
        cpus 4
        memory { 16.GB * task.attempt }
        errorStrategy = { task.attempt < 5 ? 'retry' : 'ignore' }
        maxRetries 5

        input:
                tuple val(sample), val(batch), path(assemblyPath)


        output:
                path("${sample}.*")
                publishDir "${params.results}/${batch}/${sample}/", pattern: "${sample}.bakta.*.gz", mode: 'copy'
                
        script:
                """
		bakta --db "${params.baktadb}" --prefix "${sample}.bakta" --keep-contig-headers --skip-plot --threads ${task.cpus} "${assemblyPath}"
                gzip "${sample}.bakta.tsv" "${sample}.bakta.gff3" "${sample}.bakta.gbff" "${sample}.bakta.embl" "${sample}.bakta.fna" "${sample}.bakta.ffn" "${sample}.bakta.faa" "${sample}.bakta.hypotheticals.tsv" "${sample}.bakta.hypotheticals.faa" "${sample}.bakta.json" "${sample}.bakta.txt"  
                """
}

workflow {
        log.info """\
                 B A K R E P
        ===================================
        setupdir  :   ${params.setupdir}
        samples   :   ${params.samples}
        data      :   ${params.data}
        results   :   ${params.results}
        baktadb   :   ${params.baktadb}
        gtdb      :   ${params.gtdb}
        checkm2db :   ${params.checkm2db}
        """
        .stripIndent()

        ...

        samples = channel.fromPath( params.samples )
        .splitCsv( sep: '\t', skip: 1  )
        .map( {
                def sample = it[0]
                def batch = sample.substring(3,7)
                def assemblyPath = dataPath.resolve(batch).resolve("${sample}.fa").toAbsolutePath()
                return [sample,batch,assemblyPath]
        } )

        ...

        annotation(samples)
        
}
```
