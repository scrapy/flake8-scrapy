.. _scp19:

=====================
SCP19: Non-root stack
=====================

What it does
============

Finds ``stack`` keys that are defined outside the root level of the
``scrapinghub.yml`` :ref:`shub configuration file <shub:configuration>`.


Why is this bad?
================

The ``stack`` key should always be defined at the root level of the
``scrapinghub.yml`` file to ensure that your code base uses the same
:ref:`software stack <stacks>` (Docker image, Python version) in all Scrapy
Cloud projects.


Example
=======

.. code-block:: yaml

    projects:
      default:
        id: 12345
        stack: scrapy:2.12-20241202

Instead use:

.. code-block:: yaml

    stack: scrapy:2.12-20241202
    projects:
      default:
        id: 12345
