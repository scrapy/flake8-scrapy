.. _scp21:

===========================
SCP21: No root requirements
===========================

What it does
============

Finds out if the ``requirements`` key is missing from the root of the
``scrapinghub.yml`` :ref:`shub configuration file <shub:configuration>`.


Why is this bad?
================

The ``requirements`` key in the ``scrapinghub.yml`` file is used to indicate
:ref:`Python packages to install <sc-requirements>`. It can be used to install
Python packages not included in the :ref:`stack <stacks>` or to change the
version of those.

It is important to set this requirements configuration at the root of the
``scrapinghub.yml`` file, instead of under specific projects, to ensure
consistent dependency management across all deployments of the same code base.


Example
=======

.. code-block:: yaml

    stack: scrapy:2.12-20241202

Instead use:

.. code-block:: yaml

    stack: scrapy:2.12-20241202
    requirements:
      file: requirements.txt
