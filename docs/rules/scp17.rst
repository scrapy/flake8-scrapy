.. _scp17:

==============================
SCP17: Redundant setting value
==============================

What it does
============

Finds settings in a settings module (e.g. ``settings.py``) that are set to
their default value and are not :ref:`changing settings <scp34>`.


Why is this bad?
================

Setting a setting to its default value is generally unnecessary, and can be
misleading.

Do it only if:

-   You are reverting a change made by an :ref:`add-on <topics-addons>`.

-   The default value changes in a future version of Scrapy, you will need to
    keep the current default, and you do not want to risk forgetting about it
    when you actually upgrade to that future version of Scrapy.


Example
=======

.. code-block:: python

    COOKIES_ENABLED = True

:setting:`COOKIES_ENABLED` is ``True`` by default, so this setting is redundant
and should be removed.
