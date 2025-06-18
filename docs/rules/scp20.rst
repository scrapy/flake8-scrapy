.. _scp20:

=======================
SCP20: Stack not frozen
=======================

What it does
============

Finds ``stack`` values in the ``scrapinghub.yml`` :ref:`shub configuration file
<shub:configuration>` that do not end with a date suffix in the format
``-YYYYMMDD``.


Why is this bad?
================

When you use a stack *without* a date suffix (like ``scrapy:2.12`` instead of
``scrapy:2.12-20241202``), you're using a floating tag that can change over
time as new versions are published.

Stack values should always be frozen to a specific date to ensure reproducible
deployments.


Example
=======

.. code-block:: yaml

    stack: scrapy:2.12

Instead use:

.. code-block:: yaml

    stack: scrapy:2.12-20241202
