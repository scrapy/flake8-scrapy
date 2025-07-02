.. _scp23:

==============================
SCP23: Invalid scrapinghub.yml
==============================

What it does
============

Finds invalid data in the ``scrapinghub.yml`` :ref:`shub configuration
file <shub:configuration>`, from plain syntax errors to incorrect data types
and values.


Why is this bad?
================

Using an invalid ``scrapinghub.yml`` file will cause deployment failures or
unexpected behavior.


Examples
========

Invalid requirements type:

.. code-block:: yaml

    requirements: yes

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt

Non-string stack:

.. code-block:: yaml

    stack: 2.13

Instead use:

.. code-block:: yaml

    stack: scrapy:2.13
