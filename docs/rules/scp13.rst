.. _scp13:

=====================================
SCP13: Incomplete requirements freeze
=====================================

What it does
============

Finds out if your :ref:`requirements file <requirements>` does not seem to be
fully frozen.


Why is this bad?
================

If you do not freeze all dependencies of your Scrapy project, you risk run time
errors or unexpected behavior when running your project in different
environments.

Use tools like pip-tools_ or poetry-auto-export_ to generate a requirements
file that freezes all your direct and indirect dependencies.

.. _pip-tools: https://pip-tools.readthedocs.io/en/stable/
.. _poetry-auto-export: https://github.com/Ddedalus/poetry-auto-export


Example
=======

.. code-block:: text

    scrapy>=2.11.2

Use instead:

.. code-block:: text

    attrs==25.3.0
    automat==25.4.16
    certifi==2025.6.15
    cffi==1.17.1
    charset-normalizer==3.4.2
    constantly==23.10.4
    cryptography==45.0.4
    cssselect==1.3.0
    defusedxml==0.7.1
    filelock==3.18.0
    hyperlink==21.0.0
    idna==3.10
    incremental==24.7.2
    itemadapter==0.11.0
    itemloaders==1.3.2
    jmespath==1.0.1
    lxml==5.4.0
    packaging==25.0
    parsel==1.10.0
    protego==0.4.0
    pyasn1==0.6.1
    pyasn1-modules==0.4.2
    pycparser==2.22
    pydispatcher==2.0.7
    pyopenssl==25.1.0
    queuelib==1.8.0
    requests==2.32.4
    requests-file==2.1.0
    scrapy==2.13.2
    service-identity==24.2.0
    tldextract==5.3.0
    twisted==25.5.0
    typing-extensions==4.14.0
    urllib3==2.4.0
    w3lib==2.3.1
    zope-interface==7.2