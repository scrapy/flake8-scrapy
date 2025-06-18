.. _scp25:

===================================
SCP25: Unexisting requirements.file
===================================

What it does
============

Finds ``requirements.file`` values in the ``scrapinghub.yml`` :ref:`shub
configuration file <shub:configuration>` that point to files that do not exist
in the project.


Why is this bad?
================

The ``file`` key under ``requirements`` must point to an actual file that
exists in your project. If the specified requirements file doesn't exist,
deployment to Scrapy Cloud will fail.


Example
=======

.. code-block:: yaml

    requirements:
      file: missing-requirements.txt

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
