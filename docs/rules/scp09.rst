.. _scp09:

====================================
SCP09: robots.txt ignored by default
====================================

What it does
============

Reports :setting:`ROBOTSTXT_OBEY` being missing or set to ``False`` in a
setting module (e.g. ``settings.py``).


Why is this bad?
================

The default behavior of a Scrapy project should be to respect ``robots.txt``.

Any choice to ignore it [#f1]_ should be made on a per-spider basis (e.g. in
:attr:`~scrapy.Spider.custom_settings`).

.. [#f1] There can be legitimate reasons to ignore ``robots.txt``, such as
    syntax errors.


Example
=======

.. code-block:: python

    ROBOTSTXT_OBEY = False

Use instead:

.. code-block:: python

    ROBOTSTXT_OBEY = True
