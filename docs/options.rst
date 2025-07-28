.. _options:

=======
Options
=======

Options that you can set in ``pyproject.toml``, under ``[tool.scrapy-lint]``.

.. _ignore:

ignore
======

:ref:`rules` to ignore for all files.

For example:

.. code-block:: toml

    [tool.scrapy-lint]
    ignore = ["SCP46"]


.. _known-settings:

known-settings
==============

Setting names that must not trigger :ref:`SCP27`.

For example:

.. code-block:: toml

    [tool.scrapy-lint]
    known-settings = [
        "FOO",
        "BAR",
    ]


.. _per-file-ignores:

per-file-ignores
================

:ref:`rules` to ignore for specific files.

For example:

.. code-block:: toml

    [tool.scrapy-lint.per-file-ignores]
    "spiders/toscrape_com.py" = ["SCP46"]


.. _requirements-file:

requirements-file
=================

The path to the requirements file of the Scrapy project:

.. code-block:: toml

    [tool.scrapy-lint]
    requirements-file = "path/to/my-requirements.txt"

If not specified, a requirements file is looked up as follows:

#.  The requirements file specified in ``scrapinghub.yml`` if such file exists
    and contains a root ``requirements`` key with a ``file`` value pointing to
    an existing file (path interpreted relative to the project root).

#.  The ``requirements.txt`` file in the project root directory, i.e. where
    ``scrapy.cfg`` lives.
