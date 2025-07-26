.. _scp45:

=======================
SCP45: Unsafe meta copy
=======================

What it does
============

Reports the use of :attr:`response.meta <scrapy.http.Response.meta>` when
creating a request.


Why is this bad?
================

:attr:`response.meta <scrapy.http.Response.meta>` is an alias to
:attr:`response.request.meta <scrapy.Request.meta>`, and includes request
metadata, set by components, that is specific to the corresponding request and
should not be passed on to new requests.

For example, :class:`~scrapy.downloadermiddlewares.retry.RetryMiddleware` uses
:attr:`~scrapy.Request.meta` to keep track of how many times a request has been
retried. If you pass :attr:`response.meta <scrapy.http.Response.meta>` to a new
request, you will also pass the retry count, which will lower the number of
times that the new request will be retried.


How to fix it?
==============

Options include:

-   Use :attr:`~scrapy.Request.cb_kwargs`.

    For example, instead of:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, meta={"foo": "bar"})


        def parse2(self, response):
            return response.follow("/bar", self.parse3, meta=response.meta)


        def parse3(self, response):
            foo = response.meta["foo"]

    Do:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, cb_kwargs={"foo": "bar"})


        def parse2(self, response, foo):
            return response.follow("/bar", self.parse3, cb_kwargs={"foo": foo})


        def parse3(self, response, foo): ...

-   If :attr:`~scrapy.Request.cb_kwargs` feels too verbose, use the
    scrapy-sticky-meta-params_ plugin.

    .. _scrapy-sticky-meta-params: https://github.com/heylouiz/scrapy-sticky-meta-params

    For example, instead of:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, meta={"foo": "bar"})


        def parse2(self, response):
            return response.follow("/bar", self.parse3, meta=response.meta)


        def parse3(self, response):
            foo = response.meta["foo"]

    Configure the ``StickyMetaParamsMiddleware`` middleware, set
    ``sticky_meta_keys = ["foo"]`` in your spider class, and do:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, meta={"foo": "bar"})


        def parse2(self, response):
            return response.follow("/bar", self.parse3)


        def parse3(self, response):
            foo = response.meta["foo"]

-   Explicitly map the meta keys to pass along.

    For example, instead of:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, meta={"foo": "bar"})


        def parse2(self, response):
            return response.follow("/bar", self.parse3, meta=response.meta)


        def parse3(self, response):
            foo = response.meta["foo"]

    Do:

    .. code-block:: python

        def parse(self, response):
            return response.follow("/foo", self.parse2, meta={"foo": "bar"})


        def parse2(self, response):
            return response.follow("/bar", self.parse3, meta={"foo": response.meta["foo"]})


        def parse3(self, response):
            foo = response.meta["foo"]
