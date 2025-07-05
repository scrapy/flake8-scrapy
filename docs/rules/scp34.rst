.. _scp34:

===============================
SCP34: Missing changing setting
===============================

What it does
============

Reports settings whose default value changes in a higher or planned version of
the package that defines them if those settings are not defined in your
settings module (e.g. ``settings.py``).


Why is this bad?
================

When the default value of a setting changes, it can lead to unexpected behavior
in your project if you are not aware of the change.


How to fix it
=============

Set the setting in your settings module, either to its upcoming new value or to
its current default value. That way, the upcoming default value change will not
affect your project.


Example
=======

.. code-block:: python

    FEED_EXPORT_ENCODING = "utf-8"
