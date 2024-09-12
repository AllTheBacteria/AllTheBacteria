Batch downloading from OSF
==========================

The data are all hosted on OSF: https://osf.io/xv7q9/

If you only want a few files, then browsing the website an manually downloading
works fine. This page describes how to download files in bulk.
It is not immediately obvious how to do so, because you need to
get the URLs of the files you want to download.


All latest files
----------------

We provide a tab-delimited file of all the files that are on OSF for the whole
AllTheBacteria project: `all_atb_files.tsv <https://osf.io/xv7q9/>`_.
This is subject to change, and is updated when files change on OSF.

The columns are:

* ``project``: the name of the project/component, plus its parents, with the
  names separated by ``/``. For example
  the Metadata component sits directly under the main AllTheBacteria project,
  and is called ``AlTheBacteria/Metadata``.
* ``project_id``: the project identifier. This is useful if you want to
  make your own file list (see below)
* ``filename``: the name of the file
* ``url``: the URL of the file
* ``md5``: the MD5 sum of the file
* ``size(MB)``: size of the file in MB


Using this file, it is then relatively easy to batch download. For example, the
ENA metadata file for release 0.2 has this information::

    project     AllTheBacteria/Metadata
    project_id  h7wzy
    filename    0.2/ena_metadata.tsv.gz
    url         https://osf.io/download/6661ba5c65e1de509c893bb6/
    md5         47d03a4892ae6ec5f337c9854e67b7af

You could use ``wget`` to download::

    wget -O ena_metadata.tsv.gz https://osf.io/download/6661ba5c65e1de509c893bb6/

and then check the MD5 sum is correct.


Making file lists
-----------------

Ignore this section if you just want to use the file list provided by us.
Otherwise, keep reading.

A file list can be made with this script:
https://github.com/martinghunt/bioinf-scripts/blob/master/python/osf_get_files_for_project.py

It gathers all the files for one component on OSF, taking the identifier you
see in the component's URL as input. It recursively finds all descendants
of component that you give it, in other words, all of the sub-projects/components
underneath the main component.

The default output format is TSV, which is what we use to make the
lists that go on OSF, with the columns as described above.
You can instead get JSON output, which returns
all the metadata for each file, with ``--format json``. This contains
a large amount of data!


Get all the files
~~~~~~~~~~~~~~~~~

The project identifier of AllTheBacteria is ``xv7q9``. The file
``all_atb_files.tsv`` is made with::

    osf_get_files_for_project.py xv7q9 > all_atb_files.tsv


Files for one project
~~~~~~~~~~~~~~~~~~~~~

You need to find the project identifier to input to
``osf_get_files_for_project.py``. This will be in the file
``all_atb_files.tsv`` (the ``project_id`` column),
or at the end of the URL in your browser.
For example, the URL of the metadata component is https://osf.io/h7wzy/ and you
need to input ``h7wzy`` to the script. The usage is::

    osf_get_files_for_project.py h7wzy > file_list.tsv

(replace ``h7wzy`` with the appropriate string depending on the
component you want).

