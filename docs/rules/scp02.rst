.. _scp02:

====================================
SCP02: URLs found in allowed_domains
====================================

What it does
============

Finds URLs in :attr:`~scrapy.Spider.allowed_domains` instead of domain names.


Why is this bad?
================

The :attr:`~scrapy.Spider.allowed_domains` attribute should contain domain names
only, not full URLs.


Example
=======

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"
        allowed_domains = ["https://toscrape.com/"]

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"
        allowed_domains = ["toscrape.com"]
