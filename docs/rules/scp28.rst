.. _scp28:

===============================
SCP28: Non-mapping requirements
===============================

What it does
============

Finds ``requirements`` keys in the ``scrapinghub.yml`` :ref:`shub configuration
file <shub:configuration>` that are not mappings_.

.. _mappings: https://yaml.org/spec/1.2.2/#mapping


Why is this bad?
================

The ``requirements`` configuration in ``scrapinghub.yml`` must be a mapping.
See :ref:`shub:configuration`.


Example
=======

.. code-block:: yaml

    requirements: yes

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
