.. _scp19:

=====================
SCP19: Non-root stack
=====================

What it does
============

Finds ``stack`` keys that are defined outside the root level of the
``scrapinghub.yml`` :ref:`shub configuration file <shub:configuration>`,
including ``stacks.default`` usage.


Why is this bad?
================

The ``stack`` key should always be defined at the root level of the
``scrapinghub.yml`` file to ensure that your code base uses the same
:ref:`software stack <stacks>` (Docker image, Python version) in all Scrapy
Cloud projects.

While ``stacks.default`` is a valid way to define a stack, using a root
``stack`` key is more readable and follows the recommended best practice.
The root ``stack`` key is more explicit and consistent with other root-level
configuration options.


Examples
========

Non-root stack in projects:

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

Using ``stacks.default``:

.. code-block:: yaml

    projects:
      prod: 12345
      dev: 345
    requirements:
      file: requirements.txt
    stacks:
      default: "scrapy:2.8"

Instead use:

.. code-block:: yaml

    projects:
      prod: 12345
      dev: 345
    requirements:
      file: requirements.txt
    stack: "scrapy:2.8"
