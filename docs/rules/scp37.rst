.. _scp37:

================================
SCP37: Unpicklable setting value
================================

What it does
============

Reports a :ref:`lambda <lambda>` or :ref:`generator expression <genexpr>` being
used in a setting value.


Why is this bad?
================

:ref:`Settings <topics-settings>` must be :ref:`picklable <pickle-picklable>`.


Example
=======

.. code-block:: python
    :caption: ``settings.py``

    FEED_URI_PARAMS = lambda params, spider: {}

Instead use:

.. code-block:: python
    :caption: ``settings.py``

    def feed_uri_params(params, spider):
        return {}


    FEED_URI_PARAMS = feed_uri_params
