.. _scp16:

===============================
SCP16: Unmaintained requirement
===============================

What it does
============

Finds out if your :ref:`requirements file <requirements>` contains a package
that is no longer maintained.


Why is this bad?
================

Using software with known security vulnerabilities exposes your application to
potential security risks.


Example
=======

.. code-block:: text

    scrapy-splash

Instead use:

.. code-block:: text

    scrapy-playwright
