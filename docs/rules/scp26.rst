.. _scp26:

=================================
SCP26: requirements.file mismatch
=================================

What it does
============

Finds ``requirements.file`` values in the ``scrapinghub.yml`` :ref:`shub
configuration file <shub:configuration>` that point to a different file than
the one determined by the :ref:`requirements file resolution logic
<requirements>`.


Why is this bad?
================

When you specify a requirements file using the :ref:`scrapy-requirements-file`
option, but your ``scrapinghub.yml`` points to a different requirements file,
this creates an inconsistency between the requirements file that flake8-scrapy
checks and the one that you deploy to Scrapy Cloud.


Example
=======

With ``--scrapy-requirements-file=requirements-dev.txt``:

.. code-block:: yaml

    stack: scrapy:2.12-20241202
    requirements:
      file: requirements.txt

Instead use:

.. code-block:: yaml

    stack: scrapy:2.12-20241202
    requirements:
      file: requirements-dev.txt

Or update your Flake8 configuration to use the same file as specified in
``scrapinghub.yml``.
