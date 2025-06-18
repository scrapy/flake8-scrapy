.. _pre-commit:

==========
pre-commit
==========

When using `pre-commit <https://pre-commit.com/>`__, configure Flake8 and list
flake8-scrapy in ``additional_dependencies``:

.. code-block:: yaml

    - repo: https://github.com/pycqa/flake8
      rev: "7.2.0"
      hooks:
      - id: flake8
        additional_dependencies:
        - flake8-scrapy
