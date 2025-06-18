.. _scp24:

================================
SCP24: Invalid requirements.file
================================

What it does
============

Finds ``requirements.file`` values in the ``scrapinghub.yml`` :ref:`shub
configuration file <shub:configuration>` that are not valid non-empty strings.


Why is this bad?
================

The ``file`` key under ``requirements`` must contain a valid file path as a
non-empty string. Invalid values like empty strings, null values, numbers, or
other data types will cause deployment failures or unexpected behavior.

A valid requirements file path should point to an actual requirements file
(typically ``requirements.txt``) that contains the Python package dependencies
for your project.


Example
=======

.. code-block:: yaml

    requirements:
      file: ""

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
