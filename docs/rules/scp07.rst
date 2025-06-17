.. _scp07:

========================
SCP07: Redefined setting
========================

What it does
============

Finds lines in setting modules (e.g. ``settings.py``) that define a setting
that had already been defined in a previous line.


Why is this bad?
================

It is rarely done intentionally, and when unintentional, it is often
problematic.


Example
=======

.. code-block:: python

    ADDONS = {foo.Addon: 100}
    ...
    ADDONS = {bar.Addon: 200}


Use instead:

.. code-block:: python

    ADDONS = {
        foo.Addon: 100,
        bar.Addon: 200,
    }
