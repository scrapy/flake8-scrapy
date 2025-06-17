.. _scp05:

======================
SCP05: lambda callback
======================

What it does
============

Finds :ref:`lambdas <lambda>` used as :attr:`~scrapy.Request.callback` or
:attr:`~scrapy.Request.errback`.


Why is this bad?
================

While lambdas can work as request callbacks, they will become an issue if you
ever start using :setting:`JOBDIR`, since lambdas are not serializable.


Example
=======

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def start(self):
            yield scrapy.Request(
                url="https://toscrape.com",
                callback=lambda response: {"title": response.css("h1::text").get()},
            )

Use instead:

.. code-block:: python

    import scrapy


    class MySpider(scrapy.Spider):
        name = "myspider"

        def start(self):
            yield scrapy.Request(
                url="https://toscrape.com",
                callback=self.my_callback,
            )

        def my_callback(self, response):
            yield {"title": response.css("h1::text").get()}
