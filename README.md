# scrapy-flake8

![](https://github.com/stummjr/flake8-scrapy/workflows/CI/badge.svg)
![](https://pepy.tech/badge/flake8-scrapy)

A [Flake8](https://flake8.pycqa.org/en/latest/) plugin to catch common issues
on Scrapy projects.

## Error codes

| Code  | Meaning |
| ---   | --- |
| SCP01 | There are URLs in `start_urls` whose netloc is not in `allowed_domains` |
| SCP02 | There are URLs in `allowed_domains` |
| SCP03 | Usage of `urljoin(response.url, '/foo')` instead of `response.urljoin('/foo')` |
| SCP04 | Usage of `Selector(response)` in callback |


## Installation

```
$ pip install flake8-scrapy
```


## Usage

Once installed, flake8-scrapy checks are run automatically when running
[Flake8](https://flake8.pycqa.org/en/latest/):

```
$ flake8
```
