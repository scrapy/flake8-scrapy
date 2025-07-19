.. _scp38:

=============================
SCP38: Low project throttling
=============================

What it does
============

Reports a setting module (e.g. ``settings.py``) where:

-   :setting:`CONCURRENT_REQUESTS_PER_DOMAIN` is higher than ``1``.

-   :setting:`DOWNLOAD_DELAY` is lower than ``1.0``.


Why is this bad?
================

Your setting module defines the default settings for all your spiders.

Even if all your current spiders target websites that can handle low
throttling, it is recommended [1]_ to set higher throttling values (i.e. lower
concurrency, higher delay), in case future spiders target websites that are
more sensitive to scraping load.

Additional, more granular adjustments can be made on a per-domain basis
(:setting:`DOWNLOAD_SLOTS`) or on a per-spider basis (e.g. in
:attr:`~scrapy.Spider.custom_settings`).

.. [1] In Scrapy 2.13.3+, :command:`startproject` sets these recommendations in
    ``settings.py``.


Example
=======

.. code-block:: python

    CONCURRENT_REQUESTS_PER_DOMAIN = 8
    DOWNLOAD_DELAY = 0.0

Instead use:

.. code-block:: python

    CONCURRENT_REQUESTS_PER_DOMAIN = 1
    DOWNLOAD_DELAY = 1.0
