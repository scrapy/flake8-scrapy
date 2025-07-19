.. _scp10:

====================================
SCP10: Incomplete project throttling
====================================

What it does
============

Reports a setting module (e.g. ``settings.py``) where
:setting:`CONCURRENT_REQUESTS_PER_DOMAIN` and :setting:`DOWNLOAD_DELAY` are not
both set.


Why is this bad?
================

A Scrapy project should set sane defaults for throttling settings based on the
kind of websites that it aims to scrape.

Additional, more granular adjustments can be made on a per-domain basis
(:setting:`DOWNLOAD_SLOTS`) or on a per-spider basis (e.g. in
:attr:`~scrapy.Spider.custom_settings`).


Example
=======

.. code-block:: python

    CONCURRENT_REQUESTS_PER_DOMAIN = 1
    DOWNLOAD_DELAY = 1.0
