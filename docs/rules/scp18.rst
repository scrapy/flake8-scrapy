.. _scp18:

====================
SCP18: No root stack
====================

What it does
============

Finds out if the ``stack`` key is missing from the root of the
``scrapinghub.yml`` :ref:`shub configuration file <shub:configuration>`.


Why is this bad?
================

The ``stack`` key in the ``scrapinghub.yml`` file specifies the :ref:`software
stack <stacks>` to use: Docker_ image, Python version, and Python packages.

.. _Docker: https://www.docker.com/

While you can (and *should*) set your Python packages through your
:ref:`requirements file <requirements>`, the ``stack`` allows you to freeze the
Docker image and Python version that your project uses in :ref:`Scrapy Cloud
<scrapy-cloud>`.

And it is important to set this stack at the root of the ``scrapinghub.yml``
file, instead of e.g. under a specific Scrapy Cloud project, because you do not
want to accidentally use the default stack when deploying to a Scrapy Cloud
project that does not have a stack explicitly configured. And it generally
makes sense that the same code base always uses the same stack.


Example
=======

.. code-block:: yaml

    requirements:
      file: requirements.txt

Instead use:

.. code-block:: yaml

    requirements:
      file: requirements.txt
    stack: scrapy:2.12-20241202
