.. _scp46:

==========================
SCP46: Raw Zyte API params
==========================

What it does
============

When using :doc:`scrapy-zyte-api <scrapy-zyte-api:index>`, reports the use of
:reqmeta:`zyte_api` in :attr:`meta <scrapy.Request.meta>` or the
:setting:`ZYTE_API_DEFAULT_PARAMS` setting.


Why is this bad?
================

:reqmeta:`zyte_api` is used to send raw parameters to Zyte API. Unlike
:reqmeta:`zyte_api_automap`, it does not automatically map
:class:`~scrapy.Request` parameters (besides :attr:`~scrapy.Request.url`) to
Zyte API parameters.

Similarly, :setting:`ZYTE_API_DEFAULT_PARAMS` is used to set default parameters
for requests that use raw Zyte API parameters. When using
:setting:`ZYTE_API_TRANSPARENT_MODE` (default) or :reqmeta:`zyte_api_automap`,
you must use :setting:`ZYTE_API_AUTOMAP_PARAMS` instead of
:setting:`ZYTE_API_DEFAULT_PARAMS`.


Example
=======

If using :setting:`ZYTE_API_TRANSPARENT_MODE` and params that :ref:`can be
automatically mapped <request-automatic>`, instead of:

.. code-block:: python

    Request(url, meta={"zyte_api": {"httpResponseBody": True}})

Remove the meta key altogether and let automatic mapping do its job:

.. code-block:: python

    Request(url)

If you need to set Zyte API param with no equivalent in
:class:`~scrapy.Request`, instead of:

.. code-block:: python

    Request(url, meta={"zyte_api": {"httpResponseBody": True, "geolocation": "ie"}})

Use :reqmeta:`zyte_api_automap`:

.. code-block:: python

    Request(url, meta={'zyte_api_automap': {"geolocation": "ie"}})