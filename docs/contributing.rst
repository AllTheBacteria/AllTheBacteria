Contributing to AllTheBacteria
==============================

We welcome contributions to AllTheBacteria. Please read on for instructions
on how to contribute to the project.

Background information
----------------------

Where do all the files live?

* Assemblies, metadata and all analysis files are hosted at the
  AllTheBacteria project on OSF: https://osf.io/xv7q9/.
  ie this is where we expect users of the data to go.
* Files to reproduce the analyses (scripts, methods descriptions) are on the
  AllTheBacteria GitHub repository: https://github.com/AllTheBacteria/AllTheBacteria.
  This is where contributors should add their reproducibility files, and where
  anyone should look for methods as opposed to the actual data.
  The exception is large files (eg containers or databases), which go on OSF.
* Documentation for the end-user (ie how can I get and use the data?) is here
  on readthedocs.

Before starting
^^^^^^^^^^^^^^^

Before starting any work that you intend to contribute, please check if it has
already been done (it's already on the  OSF AllTheBacteria project) or is
already on the to do/in progress list
(see the `AllTheBacteria GitHub planning project <https://github.com/orgs/AllTheBacteria/projects/1/views/1>`_).

Every task on the project page should link to a GitHub issue. If the work
you are interested in is already in progress and you want to comment and/or
help, then please reply to the relevant existing GitHub issue.

To contribute, you will need:

* A `GitHub <https://github.com>`_ account
* An `OSF <https://osf.io>`_ account


Making your analyses reproducible
----------------------------------

Please consider reproducibility before running any analysis.

Methods and scripts should be ultimately added to the public
AllTheBacteria GitHub repository. At a minimum, this means anyone should be
able to figure out exactly what you ran (tool versions, commands etc) and have
access to any scripts that were used. If not already publicly available,
we will insist that any containers used are added to OSF.

We understand that everyone works differently. It is perfectly reasonable to
make a script/pipeline that you used to run on your own compute cluster,
knowing that it would likely break if someone else tried running it elsewhere.
We just require that all scripts are made available, so that the process is
clearly documented, even though it is not necessarily easy to rerun.
For a concrete example see the
`checkm2 analysis <https://github.com/AllTheBacteria/AllTheBacteria/tree/main/reproducibility/All-samples/checkm2>`_,
which was run on the EBI cluster using SLURM.
Alternateively, if you have bandwidth, please ask the community
(via email or the MicroBio Slack channel) whether anyone is willing to help
you make it reproducible.


SOP for contributing
--------------------

Please note that this is a general standard operating procedure (SOP)
intended to cover most cases.
However, every analysis is different. Please ask or suggest something
different if it makes sense to do so for your analysis. The overall aim
is to make it as easy as we can for users to download the results from
OSF, and the methods/reproducibility to be documented as clearly and
comprehensively as possible.




Register your planned work on GitHub
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

First, make a new `AllTheBacteria GitHub issue <https://github.com/AllTheBacteria/AllTheBacteria/issues>`_
describing what you intend to do.
This should get picked up by one of the admins, who will:

* agree that the analysis can be added to AllTheBacteria
* add a new piece of work in the to-do column of the `AllTheBacteria GitHub
  project <https://github.com/orgs/AllTheBacteria/projects/1/views/1>`_,
  linked to the GitHub issue you created.
* Reply to the issue with the link to an OSF project component, which is where
  the final analysis files will be shared. You will need to log into OSF and
  request access to that component, so that you can upload your files later.



Carry out the analysis
^^^^^^^^^^^^^^^^^^^^^^

Run your analysis, but please bear in mind reproducibility and ease of use of
the output files. Essentially, please be sensible, imagine you are the end-user
of your data and think about the format that you would want it in.

Please:

* Take note of all commands that were run and software versions. This
  information can be added to the reproducibility files on Github later.
* Track all samples using the SAM* accession.
* Keep track of which samples/releases you ran on. At the time of writing
  there is release 0.2 plus incremental release 2024-08.
* We will require a "status" file that lists each sample and a result
  of "PASS", "FAIL", "NOT DONE", so that users can easily find out the overall
  state of any sample with respect to your analysis.
* Where possible, keep raw output from tools, but concatenate files into one
  output file instead of sharing millions files. But make sure the samples and
  their results are identifiable. For example, if the file is csv/tsv,
  then add a Sample column and fill this with the SAM* accession.
* Compress final files with gzip or xz (with the -9 option for maximum
  compression).
* Where possible and it makes sense to do so, keep the number of files and
  total size to a minimum.



Add files to OSF
^^^^^^^^^^^^^^^^

You should have been given access to an OSF project component,
where you can upload results files. Please include an overall "status" file (as
described above) together will all the other results.

OSF has a file size limit of 5GB, and a project component limit of 50GB.
We can work around the 50GB limit by batching files over more than one
component. Request this on your GitHub issue if it is needed and we can create
more components. For example, see the
`assembly files <https://osf.io/zxfmy/>`_,
which are split over two components.

If possible, please organise the files inside the component by having
top-level folders named with the version number of the tool that was run.
Inside there, have a folder of each batch of data the analysis was run
on (for example, release
0.2, incremental release 2024-08), and also a folder that has
all results aggregated together, so it is easy for the user to get them.
This of course may depend on your analysis, for example the
`AMRfinderPlus results <https://osf.io/7nwrx/>`_ have an extra layer
of versions because there is the tool version, but also the version of
the reference database that was used.


The intention is that reproducibility files are kept
on GitHub, however some files will be too big. Please note:

* If you used a container that is not publicly available (eg biocontainers or
  similar), then add the file to OSF inside a folder called “reproducibility”.
  For singularity, upload the image file. For docker, archive the container with
  ``docker save foo > bar.tar`` and put the archive on OSF.
* Any other “big” files (ie too big to be sensible for git) that were used as
  part of running the analysis should also be uploaded to OSF. Unless they
  are far too big and can be obtained elsewhere (eg the AMRFinderplus database
  is small, but the Bakta database is huge).


GitHub pull request
^^^^^^^^^^^^^^^^^^^

Please send a pull request to the
`AllTheBacteria github repository <https://github.com/AllTheBacteria/AllTheBacteria>`_
that:

1. refers to the GitHub issue related to the analysis (the issue you originally made),
2. adds documentation to readthedocs, and
3. includes reproducibility files.

Notes on the documentation:

* this should be instructions for any user who will want to
  download your analysis files and use them.
* The documentation is in the ``docs/`` folder.
* If you are adding a new page, then this means adding a new ``.rst`` file
  and adding its name (without the ``.rst``) to the ``toctree`` section of the
  index file ``index.rst``. For example, if the new file is ``foo.rst``, then
  also add ``foo`` to the index file.
* The title that is in the ``foo.rst`` file - defined by the first line of the
  file followed by a line of ``====`` of the same length - is what will appear in
  the contents panel on the left of the readthedocs pages. Please name
  this sensibly.
* The order of files in the ``index.rst`` file is the same as the order that
  is shown in readthedocs. If you add a new file, please put it in an order
  that seems sensible.
* You can build a local copy of the documentation by running
  ``sphinx-build -b html -d _build/doctrees . OUT/html``. This assumes that
  sphinx is installed (on Ubuntu the package is ``python3-sphinx``), and
  also the python package ``sphinx_rtd_theme`` (which is pip installable)
* when the pull request is merged, readthedocs at
  https://allthebacteria.readthedocs.io/en/latest/ will be automatically
  rebuilt with the changes.


Notes on reproducibility files:

* Please add a new directory that contains all of your new files.
  If it is across all species, then put it in ``reproducibility/All-samples/``,
  otherwise put it in ``reproducibility/Species-specific/``.
* Include a ``README.md`` file that describes the analysis and/or methods.
  In particular, commands run and software versions etc.
* Include all scripts that were run. If things are hard-coded or in other ways
  specific to how/where you ran, making them hard to run for others,
  please note this in the README.

In addition to checking the GitHub files in the pull request, the files added
to OSF will also be checked. Once the PR is accepted, that is also saying that
we are happy with the changes to both GitHub and OSF.

