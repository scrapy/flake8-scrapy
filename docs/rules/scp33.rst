.. _scp33:

=======================
SCP33: Base setting use
=======================

What it does
============

Reports the use of a ``_BASE``-suffixed setting, e.g.
:setting:`DOWNLOAD_HANDLERS_BASE`.


Why is this bad?
================

Base settings are not meant to be used directly. Instead, you should use
the corresponding setting without the ``_BASE`` suffix, which is
automatically populated with the values from the matching base setting.

To remove base entries from regular settings that have a base setting, set the
key if that entry to ``None`` in the regular setting.


Example
=======

To disable ``file://`` downloads, do not change
:setting:`DOWNLOAD_HANDLERS_BASE`:

.. code-block:: python

    from scrapy.settings.default_settings import DOWNLOAD_HANDLERS_BASE

    DOWNLOAD_HANDLERS_BASE = {
        k: v for k, v in DOWNLOAD_HANDLERS_BASE.items() if k != "file"
    }

Instead, set ``"file"`` to ``None`` in :setting:`DOWNLOAD_HANDLERS`:

.. code-block:: python

    DOWNLOAD_HANDLERS = {
        "file": None,
    }
