.. _scp12:

=======================
SCP12: Imported setting
=======================

What it does
============

Reports all-uppercase objects being imported into a Scrapy settings module
(e.g. ``settings.py``).


Why is this bad?
================

Importing settings directly can make it harder to track where settings are
defined and can lead to confusion about the source of truth for configuration
values.

When you need to import a setting from another module, the recommended approach
is to import the module and re-define the setting locally, which makes the
setting definition explicit and easier to maintain.


Example
=======

.. code-block:: python

    from foo import FOO


Use instead:

.. code-block:: python

    import foo

    FOO = foo.FOO
