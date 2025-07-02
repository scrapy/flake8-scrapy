.. _scp24:

=================================
SCP24: Missing stack requirements
=================================

What it does
============

Finds out if your :ref:`requirements file <requirements>` is missing packages
that are pre-installed in your Scrapy Cloud stack.


Why is this bad?
================

When deploying to Scrapy Cloud, your project's requirements should include all
packages that may be pre-installed in the cloud environment to avoid dependency
conflicts.

For example, if your requirements.txt installs ``packageA==1.0`` and Scrapy
Cloud has ``packageB==1.0`` pre-installed, you could end up with conflicting
dependencies if ``packageA==1.0`` depends on ``packageC>=2.0`` while
``packageB==1.0`` depends on ``packageC<2.0``. This results in a broken
installation.

By including all stack packages in your requirements file, along with a
:ref:`complete freeze <scp13>`, you ensure that dependency resolution accounts
for all packages and their version constraints, preventing conflicts.
