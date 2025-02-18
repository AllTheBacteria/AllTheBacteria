nextflow.enable.dsl=2

/*
        Runs GTDBtk for taxonomic classification.
*/

process taxonomy {

        tag "${sample}"
        conda "bioconda::gtdbtk=2.4.0"
        cpus 1
        memory  { 32.GB * task.attempt }
        errorStrategy = { task.attempt < 5 ? 'retry' : 'ignore' }
        maxRetries 5

        input:
                tuple val(sample), val(batch), path(assemblyPath)

        output:
                path("${sample}.gtdbtk.json.gz")
                publishDir "${params.results}/${batch}/${sample}/", pattern: "${sample}.gtdbtk.json.gz", mode: 'copy'

        script:
                """
                export GTDBTK_DATA_PATH="${params.gtdb}"
                mkdir -p ./tmp_gtdbtk
                cp ${assemblyPath} ./tmp_gtdbtk
                gtdbtk classify_wf --genome_dir "./tmp_gtdbtk" --out_dir "./" --prefix "${sample}" --extension fa --pplacer_cpus 1 --mash_db "${params.db}/gtdbtk_mash/"
                ParseToJSON_gtdbtk.py -i "${sample}.bac120.summary.tsv" -o "${sample}.gtdbtk.json"
                gzip "${sample}.gtdbtk.json"
                """
}

/*
        Runs CheckM2 for assessing the quality of the genomes.
        CheckM2 is the new version of CheckM which uses a machine learning approach for quality assessement.
*/

process qualityCheck {

        tag "${sample}"
        conda "checkm2=1.0.2"
        cpus 1
        memory { 20.GB * task.attempt }
        errorStrategy = { task.attempt < 5 ? 'retry' : 'ignore' }
        maxRetries 5

        input:
                tuple val(sample), val(batch), path(assemblyPath)

        output:
                path("${sample}.checkm2.json.gz")
                publishDir "${params.results}/${batch}/${sample}/", pattern: "${sample}.checkm2.json.gz", mode: 'copy'

        script:
                """
                mkdir -p ./tmp_qc
                cp ${assemblyPath} ./tmp_qc
                checkm2 predict --input ./tmp_qc --output-directory ./qc -x .fa --database_path ${params.checkm2db}
                ParseToJSON_checkm2.py -i "./qc/quality_report.tsv" -o "${sample}.checkm2.json"
                gzip "${sample}.checkm2.json"
                """
}

process assemblyScan {

        tag "${sample}"
	conda "assembly-scan"
        cpus 1
        memory { 2.GB * task.attempt }
        errorStrategy = { task.attempt < 5 ? 'retry' : 'ignore' }
        maxRetries 5

        input: tuple val(sample), val(batch), path(assemblyPath)

        output:
                path("${sample}.assemblyscan.json.gz")
                publishDir "${params.results}/${batch}/${sample}/", pattern: "${sample}.assemblyscan.json.gz", mode: 'copy'

        script:
                """
                mkdir -p  ./tmp_scan
                cp ${assemblyPath} ./tmp_scan
                assembly-scan ./tmp_scan/* --json > ${sample}.assemblyscan.json
                gzip "${sample}.assemblyscan.json"
                """
}

/*
        Runs mlst for multilocus-sequence-typing.
*/

process mlst {

        tag "${sample}"
        conda "mlst=2.23.0"
        cpus 1
        memory { 2.GB * task.attempt }
        errorStrategy = { task.attempt < 5 ? 'retry' : 'ignore' }
        maxRetries 5

        input:
                tuple val(sample), val(batch), path(assemblyPath)

        output:
                path("${sample}.mlst.json.gz")
                publishDir "${params.results}/${batch}/${sample}/", pattern: "${sample}.mlst.json.gz", mode: 'copy'

        script:
                """
                mkdir -p ./tmp_mlst
                cp ${assemblyPath} ./tmp_mlst
                mlst --json "${sample}.mlst.json" --label "${sample}" ./tmp_mlst/*
                gzip "${sample}.mlst.json"
                """
}

/*
        Runs Bakta for annotation.
*/

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

/*
        Setupdir where the databases and input files are located.
*/
        if(params.setupdir == null) {
    println('Setup directory is null! Please provide the setup directory via --setupdir')
    System.exit(-1)
}
/*
        Option to stop the pipeline in the case the specified output_dir is not empty.
*/
        results = Path.of(params.results).toAbsolutePath()

        if (results != null && results.list().size() != 0) {
    println "!!! WARNING: Directory $results is not empty. Rsync will overwrite existing files. !!!"
    //System.exit(-1)
        }

/*
        Coverts the user input of the the data folder to an absolute path and checks if the folder really contains data.
*/

        def dataPath = null
        if(params.data != null) {
                dataPath = Path.of(params.data).toAbsolutePath()
                        if (dataPath.list().size() == 0) {
                                println "WARNING: Directory $dataPath is empty."
                                System.exit(-1)
                                }
        } else {
                println('Data directory is null! Please provide the Data directory path via --data')
                System.exit(-1)
}

/*
        Collects specific parameters from the metadata file.
        Defines the full file path from the user input and the folder name, which is a substring of the sample id.
*/

        samples = channel.fromPath( params.samples )
        .splitCsv( sep: '\t', skip: 0  )
        .map( {
                def sample = it[2]
                def batch = sample.substring(3,7)
                def assemblyPath = dataPath.resolve(batch).resolve("${sample}.fa").toAbsolutePath()
                return [sample,batch,assemblyPath]
        } )


    
        
        taxonomy(samples)
        qualityCheck(samples)
        assemblyScan(samples)
        mlst(samples)
        annotation(samples)
        
}

