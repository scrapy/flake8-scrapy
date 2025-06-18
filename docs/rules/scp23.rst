.. _scp23:

===========================
SCP23: No requirements.file
===========================

What it does
============

Finds ``requirements`` keys in the ``scrapinghub.yml`` :ref:`shub configuration
file <shub:configuration>` that do not contain a nested ``file`` key.


Why is this bad?
================

The ``requirements`` configuration in ``scrapinghub.yml`` must specify how to
install Python packages. The most common way to do this is by referencing a
requirements file using the ``file`` key.

Without the ``file`` key, the requirements configuration is incomplete and
won't actually install any packages when deployed to Scrapy Cloud.


Example
=======

.. code-block:: yaml

    requirements:

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
