.. _scp03:

====================================
SCP03: urljoin(response.url, "/foo")
====================================

What it does
============

Finds usage of :func:`~urllib.parse.urljoin` that can be replaced with
:meth:`Response.urljoin() <scrapy.http.Response.urljoin>`.


Why is this bad?
================

:meth:`Response.urljoin() <scrapy.http.Response.urljoin>`

* uses the HTML ``<base>`` tag to properly resolve relative URLs,
* doesn't require an extra import, and
* is more readable.

Example
=======

.. code-block:: python

    import scrapy
    from urllib.parse import urljoin


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            yield {"homepage": urljoin(response.url, "/")}

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def parse(self, response):
            yield {"homepage": response.urljoin("/")}
