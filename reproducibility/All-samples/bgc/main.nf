nextflow.enable.dsl=2
workflow {
    genomes = Channel
    .fromPath("/path_to_genomes/*.fa")
    .map{file -> tuple(file.simpleName, file)}
    gecco(genomes)    
}

process gecco {
  container '/path_to_container/gecco_0.9.8--pyhdfd78af_0.sif'
  input:
  tuple val (prefix), path(genome)
  output:
  tuple val(prefix),path("${prefix}/")
  script:
  """
  gecco run -j ${task.cpus} --genome ${genome} --o ${prefix}/ --mask
  """
}
