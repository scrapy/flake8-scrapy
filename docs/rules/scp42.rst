.. _scp42:

===========================
SCP42: Unneeded path string
===========================

What it does
============

Reports the use of strings instead of :class:`~pathlib.Path` objects to
represent file system paths in setting values where it is not necessary.


Why is this bad?
================

While using strings to represent paths is OK, and is sometimes necessary [1]_,
:class:`~pathlib.Path` is preferred where possible to make code more explicit
and for better typing.

.. [1] For example, strings are needed for feed URI params (see
    :setting:`FEED_URI_PARAMS`).


Example
=======

.. code-block:: python

    FEEDS = {
        "output.jsonl": {"format": "jsonl"},
    }

Instead use:

.. code-block:: python

    from pathlib import Path

    FEEDS = {
        Path("output.jsonl"): {"format": "jsonl"},
    }
