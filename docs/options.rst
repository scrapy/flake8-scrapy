.. _options:

=======
Options
=======

This is a list of options of flake8-scrapy.

See :ref:`configuration` for information on how to configure these options,
disable rules, etc.

.. _scrapy-requirements-file:

scrapy_requirements_file
========================

The path to the requirements file of the Scrapy project:

.. code-block:: ini

    [flake8]
    scrapy_requirements_file = path/to/my-requirements.txt

Only necessary if the :ref:`default lookup <requirements>` does not find the
right file.
