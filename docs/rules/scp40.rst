.. _scp40:

===========================
SCP40: Unneeded setting get
===========================

What it does
============

Reports the use of :meth:`~scrapy.settings.BaseSettings.get` to read a setting
where using subscript (``[]``) works the same, i.e. when no *default* argument
is specified or it is set to ``None``.


Why is this bad?
================

``settings["FOO"]`` is more concise and idiomatic than ``settings.get("FOO")``.


Example
=======

.. code-block:: python

    settings.get("DUPEFILTER_CLASS")

Instead use:

.. code-block:: python

    settings["DUPEFILTER_CLASS"]
