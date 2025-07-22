.. _scp44:

=================================
SCP44: requirements_file mismatch
=================================

What it does
============

When using flake8-requirements_, reports a mismatch between the requirements
file configured with the :ref:`scrapy-requirements-file` option and the one
configured with the ``requirements_file`` option of flake8-requirements_.

.. _flake8-requirements: https://pypi.org/project/flake8-requirements/


Why is this bad?
================

flake8-requirements_ will not automatically pick up the value of the
:ref:`scrapy-requirements-file` option, you must configure the
``requirements_file`` option to make flake8-requirements_ check your project
requirements file for missing packages.


Example
=======

.. code-block:: ini
    :caption: ``.flake8``

    [flake8]
    scrapy_requirements_file = custom-requirements.txt

Also use ``requirements_file``:

.. code-block:: ini
    :caption: ``.flake8``

    [flake8]
    requirements_file = custom-requirements.txt
    scrapy_requirements_file = custom-requirements.txt