.. _scp11:

==================================
SCP11: Improper setting definition
==================================

What it does
============

Reports a function or class defined with an uppercase name in a setting module
(e.g. ``settings.py``).


Why is this bad?
================

Scrapy considers any uppercase name in the settings module as a setting.

When a setting expects a function or a class as value, it is possible to set
that setting a setting module by defining a function or class with the setting
name. However, it is not recommended because it breaks Python naming
conventions for functions and classes, and makes setting modules harder to
read.


Example
=======

.. code-block:: python

    class SCHEDULER:
        pass

Instead use:

.. code-block:: python

    class MyScheduler:
        pass


    SCHEDULER = MyScheduler
