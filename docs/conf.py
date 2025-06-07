from collections.abc import Sequence

project = "flake8-scrapy"
project_copyright = "Valdir Stumm Junior"
author = "Valdir Stumm Junior"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_dark_mode",
]

html_theme = "sphinx_rtd_theme"
default_dark_mode = False

intersphinx_mapping = {
    "cssselect": ("https://cssselect.readthedocs.io/en/latest", None),
    "itemloaders": ("https://itemloaders.readthedocs.io/en/latest/", None),
    "parsel": ("https://parsel.readthedocs.io/en/latest/", None),
    "python": ("https://docs.python.org/3", None),
    "scrapy": ("https://docs.scrapy.org/en/latest/", None),
    "twisted": ("https://docs.twisted.org/en/stable/", None),
    "twistedapi": ("https://docs.twisted.org/en/stable/api/", None),
    "w3lib": ("https://w3lib.readthedocs.io/en/latest", None),
}
intersphinx_disabled_reftypes: Sequence[str] = []
