.. _scp43:

==============================
SCP43: Unsupported Path object
==============================

What it does
============

Reports the use of :class:`~pathlib.Path` objects instead of strings in
settings that do not support such objects. It also flags uses of such objects
in combination with URI params (see :setting:`FEED_URI_PARAMS`), which is not
supported.


Why is this bad?
================

Trying to use a :class:`~pathlib.Path` object in a context where it is not
supported will lead to run time errors.


Example
=======

.. code-block:: python

    from pathlib import Path

    FEEDS = {Path("output-%(time)s.json"): {"format": "json"}}

Instead use:

.. code-block:: python

    FEEDS = {"output-%(time)s.json": {"format": "json"}}
