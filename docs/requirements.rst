.. _requirements:

=================
Requirements file
=================

A requirements file is looked up as follows to enable additional rules:

#.  The :ref:`scrapy-requirements-file` option.

#.  The ``requirements_file`` option of flake8-requirements_.

    .. _flake8-requirements: https://pypi.org/project/flake8-requirements/

#.  The requirements file specified in ``scrapinghub.yml`` if such file exists
    and contains a root ``requirements`` key with a ``file`` value pointing to
    an existing file (path interpreted relative to the project root).

#.  The ``requirements.txt`` file in the project root directory, i.e. where
    ``scrapy.cfg`` lives.

To enable rules about the requirements file itself, `configure Flake8
accordingly`_:

.. _configure Flake8 accordingly: https://flake8.pycqa.org/en/latest/user/options.html#cmdoption-flake8-filename

.. code-block:: ini

    [flake8]
    filename =
        *.py,
        requirements.txt
