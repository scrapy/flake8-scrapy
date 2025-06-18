project = "flake8-scrapy"
project_copyright = "Valdir Stumm Junior"
author = "Valdir Stumm Junior"

extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.intersphinx",
    "sphinx_rtd_dark_mode",
    "sphinx_scrapy",
]

html_theme = "sphinx_rtd_theme"
default_dark_mode = False

intersphinx_mapping = {
    "flake8": ("https://flake8.pycqa.org/en/latest/", None),
}
scrapy_intersphinx_enable = [
    "shub",
    "zyte",
]
