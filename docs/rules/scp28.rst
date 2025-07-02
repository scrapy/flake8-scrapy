.. _scp28:

==============================
SCP28: Invalid scrapinghub.yml
==============================

What it does
============

Finds configuration keys in the ``scrapinghub.yml`` :ref:`shub configuration
file <shub:configuration>` that have invalid data types. Currently checks:

- ``requirements`` keys that are not mappings_
- ``stacks`` keys that are not mappings_

.. _mappings: https://yaml.org/spec/1.2.2/#mapping


Why is this bad?
================

Certain configuration keys in ``scrapinghub.yml`` must have specific data types
to be valid:

- The ``requirements`` configuration must be a mapping to properly specify
  package installation options
- The ``stacks`` configuration must be a mapping to define named stack
  configurations

Using incorrect data types will cause deployment failures or unexpected
behavior. See :ref:`shub:configuration`.


Examples
========

Invalid requirements type:

.. code-block:: yaml

    requirements: yes

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt

Invalid stacks type:

.. code-block:: yaml

    stacks: "scrapy:2.8"

Instead use:

.. code-block:: yaml

    stacks:
      default: "scrapy:2.8"
