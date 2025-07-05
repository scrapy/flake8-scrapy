.. _scp32:

===========================
SCP32: Wrong setting getter
===========================

What it does
============

Reports setting that are being read with the wrong
:class:`~scrapy.settings.Settings` method based on the setting type.


Why is this bad?
================

:class:`~scrapy.settings.Settings` provides different methods to read settings
based on their type, e.g. :meth:`~scrapy.settings.BaseSettings.getbool` or
:meth:`~scrapy.settings.BaseSettings.getint`.

:ref:`Settings <topics-settings>` can be set outside Python code, e.g. on the
command line, in which case their raw value is a string. If you do not use the
right method to read the setting, you may end up with the wrong type of
value, which can lead to bugs that are hard to track down.


Example
=======

.. code-block:: python

    settings.get("LOG_ENABLED")

Instead use:

.. code-block:: python

    settings.getbool("LOG_ENABLED")
