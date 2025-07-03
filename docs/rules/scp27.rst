.. _scp27:

======================
SCP27: Unknown setting
======================

What it does
============

Reports setting names that are not :ref:`known settings of Scrapy itself
<topics-settings>` or of any known `Scrapy plugin`_.

.. _Scrapy plugin: https://github.com/scrapy-plugins


Why is this bad?
================

Using unknown or misspelled settings can lead to silent misconfigurations.
Unrecognized settings are ignored, which means your intended configuration may
not be applied, potentially resulting in bugs or unexpected behavior.

Catching unknown settings early helps ensure that your Scrapy project is
configured as intended and reduces the risk of subtle errors.


Example
=======

The following code will trigger SCP27, because ``FOO`` is not a recognized
Scrapy setting:

.. code-block:: python
    :caption: ``settings.py``

    FOO = "bar"

Instead, use only valid Scrapy settings, such as:

.. code-block:: python
    :caption: ``settings.py``

    BOT_NAME = "mybot"
