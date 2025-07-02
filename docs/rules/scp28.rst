.. _scp28:

==============================
SCP28: Invalid scrapinghub.yml
==============================

What it does
============

Finds invalid data in the ``scrapinghub.yml`` :ref:`shub configuration
file <shub:configuration>`, from plain syntax errors to incorrect data types.
Currently checks:

- That the file is a valid YAML file
- That the root structure is a mapping_
- ``requirements`` keys that are not a mapping_
- ``stacks`` keys that are not a mapping_

.. _mapping: https://yaml.org/spec/1.2.2/#mapping


Why is this bad?
================

Using an invalid ``scrapinghub.yml`` file will cause deployment failures or
unexpected behavior. See :ref:`shub:configuration`.


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
