.. _zyte:

====
Zyte
====

If you use :ref:`Scrapy Cloud <scrapy-cloud>` and want flake8-scrapy to check
your ``scrapinghub.yml`` :ref:`configuration file <shub:configuration>`,
`configure Flake8 accordingly`_:

.. _configure Flake8 accordingly: https://flake8.pycqa.org/en/latest/user/options.html#cmdoption-flake8-filename

.. code-block:: ini

    [flake8]
    filename =
        *.py,
        scrapinghub.yml
