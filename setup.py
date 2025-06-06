import setuptools

with open("README.md", "r") as f:
    long_description = f.read()


setuptools.setup(
    name="flake8-scrapy",
    license="MIT",
    version="0.0.2",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Valdir Stumm Junior",
    author_email="stummjr@gmail.com",
    url="http://github.com/stummjr/flake8-scrapy",
    py_modules=[
        "flake8_scrapy",
        "finders",
        "finders.domains",
        "finders.oldstyle",
    ],
    entry_points={
        "flake8.extension": [
            "SCP0 = flake8_scrapy:ScrapyStyleChecker",
        ],
    },
    install_requires=["flake8"],
    tests_require=["pytest"],
    classifiers=[
        "Framework :: Flake8",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: Software Development :: Quality Assurance",
    ],
)
