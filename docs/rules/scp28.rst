.. _scp28:

=========================
SCP28: Deprecated setting
=========================

What it does
============

Reports setting names that are deprecated for the package versions frozen in
your project requirements.

It also reports the package and version in which the setting was deprecated, so
that you can check the corresponging release notes for sunset guidance.

Sometimes sunset guidance is also provided in the error message.


Why is this bad?
================

Deprecated settings will stop working in future versions of the corresponging
package.

If you do not follow sunset guidance now to migrate or remove the deprecated
setting, the next time you upgrade the corresponding package your project could
break or misbehave.
