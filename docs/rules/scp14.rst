.. _scp14:

==============================
SCP14: Unsupported requirement
==============================

What it does
============

Finds out if your :ref:`requirements file <requirements>` contains a package
that scrapy-lint supports with a frozen [#f1]_ version that scrapy-lint does
*not* support.

scrapy-lint supports many packages in the Scrapy ecosystem, but expects the
following minimum versions of them to be used in your project:

======= ===============
Package Minimum version
======= ===============
Scrapy_ 2.0.1
======= ===============

.. _Scrapy: https://scrapy.org/

.. [#f1] This rule only fires for frozen versions (using ``==``). Non-frozen
    version specifications like ``scrapy>=2.0.0`` or ``scrapy~=2.0`` are
    ignored.


Why is this bad?
================

In general, you should strive to keep up with the latest stable releases of
packages in the Scrapy ecosystem to ensure your projects benefit from the
latest features, bug fixes, and performance improvements.

However, the specific issue with using a version of a package older than the
minimum version supported by scrapy-lint is that scrapy-lint may misreport
issues and fail to report others.


Example
=======

.. code-block:: text

    scrapy==2.0.0

Use instead:

.. code-block:: text

    scrapy==2.13.2
