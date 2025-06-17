.. _scp08:

============================
SCP08: No project USER_AGENT
============================

What it does
============

Reports :setting:`USER_AGENT` being missing from a setting module (e.g.
``settings.py``).


Why is this bad?
================

Any Scrapy project should define a :setting:`USER_AGENT` setting to identify
itself to the websites it scrapes, so that they can contact you if they need
you to e.g. slow down your spider, avoid certain pages, or run at specific
hours to minimize your impact on their website.

While it is possible to define :setting:`USER_AGENT` on a specific spider or
override its value on a specific request through the ``User-Agent`` header,
having a default value in the settings module ensures that you do not
accidentally forget to set it on a spider or request.


Example
=======

.. code-block:: python

    USER_AGENT = "Jane Doe (jane@doe.example)"
