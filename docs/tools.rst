.. _tools:

===========
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
