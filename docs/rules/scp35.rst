.. _scp35:

===========================
SCP35: No-op setting update
===========================

What it does
============

Reports :ref:`pre-crawler <pre-crawler-settings>` and :ref:`reactor
<reactor-settings>` settings that are assigned a value outside a settings
module (e.g. ``settings.py``) or the :meth:`update_pre_crawler_settings` method
of an :ref:`add-on <topics-addons>`.


Why is this bad?
================

Pre-crawler settings are only taken into account when they are defined on the
command line, in a settings module, or in the ``update_pre_crawler_settings()``
method of an add-on. If defined elsewhere, their value is ignored silently.

Reactor settings are slightly different. They take effect after the crawler has
started, so they may actually be working even if they are triggering this
issue. However, they become problematic when you run multiple spiders in
parallel. Giving them a different value per spider is not possible, and usually
the value from the first spider settings is used, and any different value set
by another spider is silently ignored.


Example
=======

.. code-block:: python

    from scrapy import Spider


    class MySpider(Spider):
        name = "myspider"
        custom_settings = {
            "SPIDER_MODULES": ["myproject.myspiders"],
        }

Instead, define that setting in your settings module:

.. code-block:: python
    :caption: ``settings.py``

    SPIDER_MODULES = ["myproject.myspiders"]
