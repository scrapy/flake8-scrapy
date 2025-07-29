===========
scrapy-lint
===========

|version| |python_version| |ci|

.. |version| image:: https://img.shields.io/pypi/v/scrapy-lint.svg
   :target: https://pypi.org/pypi/scrapy-lint
   :alt: PyPI version

.. |python_version| image:: https://img.shields.io/pypi/pyversions/scrapy-lint.svg
   :target: https://pypi.org/pypi/scrapy-lint
   :alt: Supported Python versions

.. |ci| image:: https://github.com/scrapy/scrapy-lint/workflows/CI/badge.svg
   :target: https://github.com/scrapy/scrapy-lint/actions?query=workflow%3ACI
   :alt: CI

.. readme-start

**scrapy-lint** is a linter for `Scrapy <https://scrapy.org/>`_ projects.

To install::

    pip install scrapy-lint

To run::

    scrapy-lint

To use with `pre-commit <https://pre-commit.com/>`__, add the following to your
``.pre-commit-config.yaml``:

.. code-block:: yaml

    - repo: https://github.com/scrapy/scrapy-lint
      rev: "0.0.2"
      hooks:
      - id: scrapy-lint

Can be combined with `ruff <https://docs.astral.sh/ruff/>`_,
`mypy <https://mypy.readthedocs.io/en/stable/>`_,
`pylint <https://pylint.readthedocs.io/en/stable/>`_ and
`flake8-requirements <https://pypi.org/project/flake8-requirements/>`_.

.. readme-end

Documentation
=============

See the documentation_ for more.

.. _documentation: https://scrapy-lint.readthedocs.io/en/latest/
