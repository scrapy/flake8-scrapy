.. _scp41:

===========================
SCP41: Unneeded import path
===========================

What it does
============

Reports the use of import path strings instead of actual Python objects in
setting values.


Why is this bad?
================

While using import paths is not bad per se, and is sometimes necessary [1]_,
when using :ref:`release-2.4.0` or higher, it is better to use actual Python
objects (e.g. classes, functions, modules) directly in settings.

Using Python objects directly allows IDEs and static analysis tools to detect
issues at development time, such as typos or missing dependencies, and allows
IDEs to provide better autocompletion and refactoring support.

.. [1] Import paths are necessary when working with base settings, i.e. those
    suffixed with ``_BASE``.


Example
=======

.. code-block:: python

    ADDONS = {
        "scrapy_poet.Addon": 300,
    }

Instead use:

.. code-block:: python

    from scrapy_poet import Addon as ScrapyPoetAddon

    ADDONS = {
        ScrapyPoetAddon: 300,
    }
