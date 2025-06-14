=============
scrapy-flake8
=============

.. |ci| image:: https://github.com/stummjr/flake8-scrapy/workflows/CI/badge.svg
.. |downloads| image:: https://pepy.tech/badge/flake8-scrapy

|ci| |downloads|

.. intro-start

A Flake8_ plugin to catch common issues on Scrapy projects.

.. _Flake8: https://flake8.pycqa.org/en/latest/

Install
=======

::

    pip install flake8-scrapy

Use
===

Once installed, flake8-scrapy rules are checked automatically when running
Flake8_:

::

    flake8

When using `pre-commit <https://pre-commit.com/>`_, configure Flake8 and list
flake8-scrapy in ``additional_dependencies``. For example:

.. code-block:: yaml

    - repo: https://github.com/pycqa/flake8
      rev: "7.2.0"
      hooks:
      - id: flake8
        additional_dependencies:
        - flake8-scrapy

See `Configuring Flake8`_ for information on how to disable specific rules
for a project, a file or a line.

.. _Configuring Flake8: https://flake8.pycqa.org/en/latest/user/configuration.html

Other tools
===========

flake8-scrapy only implements rules not supported by better tools.

The following table lists example scenarios where other tools are useful for
Scrapy projects:

==================== ==============================================================
Tool                 Examples
==================== ==============================================================
flake8-requirements_ Missing requirements
mypy_                Defining start_urls_ as a string instead of a list
pylint_              Not calling ``super().__init__()`` (W0231_)
ruff_                Duplicate settings in dicts like custom_settings_ (F601_)
==================== ==============================================================

.. _custom_settings: https://docs.scrapy.org/en/latest/topics/spiders.html#scrapy.Spider.custom_settings
.. _F601: https://docs.astral.sh/ruff/rules/multi-value-repeated-key-literal/
.. _flake8-requirements: https://pypi.org/project/flake8-requirements/
.. _mypy: https://mypy.readthedocs.io/en/stable/
.. _pylint: https://pylint.readthedocs.io/en/stable/
.. _ruff: https://docs.astral.sh/ruff/
.. _start_urls: https://docs.scrapy.org/en/latest/topics/spiders.html#scrapy.Spider.start_urls
.. _W0231: https://pylint.readthedocs.io/en/stable/user_guide/messages/warning/super-init-not-called.html

When using flake8-requirements_, make sure to set the ``requirements-file``
option in your `Flake8 configuration`_, e.g. ``.flake8``:

.. _Flake8 configuration: https://flake8.pycqa.org/en/latest/user/configuration.html

.. code-block:: ini

    [flake8]
    requirements-file = requirements.txt

.. intro-end

Rules
=====

See the documentation_ for a list of rules.

.. _documentation: https://flake8-scrapy.readthedocs.io/en/latest/
