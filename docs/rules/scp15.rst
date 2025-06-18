.. _scp15:

===========================
SCP15: Insecure requirement
===========================

What it does
============

Finds out if your :ref:`requirements file <requirements>` contains a frozen
[#f1]_ version of a package that has known security vulnerabilities already
fixed in a higher version.

.. [#f1] This rule only fires for frozen versions (using ``==``). Non-frozen
    version specifications like ``scrapy>=2.11.1`` or ``scrapy~=2.11`` are
    ignored.


Why is this bad?
================

Using software with known security vulnerabilities exposes your application to
potential security risks.


Example
=======

.. code-block:: text

    scrapy==2.11.1

Instead use:

.. code-block:: text

    scrapy==2.13.2
