.. _scp22:

============================
SCP22: Non-root requirements
============================

What it does
============

Finds ``requirements`` keys that are defined outside the root level of the
``scrapinghub.yml`` :ref:`shub configuration file <shub:configuration>`.


Why is this bad?
================

The ``requirements`` key should always be defined at the root level of the
``scrapinghub.yml`` file to ensure consistent dependency management across
all projects in your codebase.


Example
=======

.. code-block:: yaml

    projects:
      default:
        requirements:
          file: requirements.txt

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
