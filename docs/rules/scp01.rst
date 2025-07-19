.. _scp01:

========================
SCP01: Disallowed domain
========================

What it does
============

Finds URLs in :attr:`~scrapy.Spider.start_urls` whose netloc is not in
:attr:`~scrapy.Spider.allowed_domains`.


Why is this bad?
================

The default implementation of :meth:`~scrapy.Spider.start` sets
:attr:`~scrapy.Request.dont_filter` to ``True``. As a result, URLs from
:attr:`~scrapy.Spider.start_urls` are sent by default even if their domain is
not in :attr:`~scrapy.Spider.allowed_domains`.

However, any follow-up :class:`~scrapy.Request` yielded from a
:attr:`~scrapy.Request.callback` that points to that domain will be filtered
out, which is usually not what you want.


Example
=======

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"
        allowed_domains = ["b.example"]
        start_urls = [
            "https://a.example/",
        ]

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"
        allowed_domains = ["a.example"]
        start_urls = [
            "https://a.example/",
        ]
