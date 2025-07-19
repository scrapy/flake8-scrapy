.. _scp39:

======================
SCP39: No contact info
======================

What it does
============

Reports :setting:`USER_AGENT` being assigned a value that does not seem to
contain contact information (a URL, and email address, or a phone number).


Why is this bad?
================

The owners of your target websites may sometimes want to contact you, e.g. to
report an issue or request throttling adjustments.

If you do not provide contact information in :setting:`USER_AGENT`, website
owners may not be able to contact you.


Example
=======

.. code-block:: python

    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"

Instead use:

.. code-block:: python

    USER_AGENT = "Your Name (+https://yourwebsite.example/contact)"
