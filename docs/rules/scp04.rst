.. _scp04:

=========================
SCP04: Selector(response)
=========================

What it does
============

Finds usage of :class:`~parsel.Selector` constructed with
:attr:`~scrapy.http.TextResponse` objects or response text/body that can be
replaced with response selector methods.


Why is this bad?
================

Creating a new :class:`~parsel.Selector` instance when you already have a
:class:`~scrapy.http.TextResponse` object is unnecessary and less efficient.
Scrapy's :class:`~scrapy.http.TextResponse` object provides convenient methods
like :meth:`~scrapy.http.TextResponse.xpath`,
:meth:`~scrapy.http.TextResponse.css`, and
:attr:`~scrapy.http.TextResponse.selector` that are more direct and readable.

These built-in methods also handle encoding properly and are optimized for
common use cases.


Example
=======

.. code-block:: python

    import scrapy
    from parsel import Selector


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            selector = Selector(response)
            yield {"title": selector.css("h1::text").get()}

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            yield {"title": response.css("h1::text").get()}
