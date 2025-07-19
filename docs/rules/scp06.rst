.. _scp06:

======================================
SCP06: Improper first match extraction
======================================

What it does
============

Finds uses of ``getall()[0]``, ``[0].getall()`` and similar with
:class:`~scrapy.Selector` and :class:`~scrapy.selector.SelectorList` that can
be replaced :meth:`~scrapy.selector.SelectorList.get`.


Why is this bad?
================

:meth:`~scrapy.selector.SelectorList.get` is cleaner and more efficient.


Example
=======

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            yield {"title": response.css("h1::text").getall()[0]}

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            yield {"title": response.css("h1::text").get()}
