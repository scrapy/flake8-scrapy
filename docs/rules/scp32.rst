.. _scp32:

===========================
SCP32: Wrong setting method
===========================

What it does
============

Reports setting that are being read or updated with the wrong
:class:`~scrapy.settings.Settings` method based on the setting type.


Why is this bad?
================

-   :class:`~scrapy.settings.Settings` provides different methods to read
    settings based on their type, e.g.
    :meth:`~scrapy.settings.BaseSettings.getbool` or
    :meth:`~scrapy.settings.BaseSettings.getint`.

    :ref:`Settings <topics-settings>` can be set outside Python code, e.g. on
    the command line, in which case their raw value is a string. If you do not
    use the right method to read the setting, you may end up with the wrong
    type of value, which can lead to bugs that are hard to track down.

-   :class:`~scrapy.settings.Settings` also provides methods to edit settings
    that are only meant to work on settings of a given type, such as
    :meth:`~scrapy.settings.BaseSettings.add_to_list`, to work on lists, or
    :meth:`~scrapy.settings.BaseSettings.replace_in_component_priority_dict`,
    to work on :ref:`component priority dictionaries
    <component-priority-dictionaries>`.


Example
=======

.. code-block:: python

    settings.get("LOG_ENABLED")

Instead use:

.. code-block:: python

    settings.getbool("LOG_ENABLED")
