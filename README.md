# scrapy-flake8
![](https://github.com/stummjr/flake8-scrapy/workflows/CI/badge.svg)
![](https://pepy.tech/badge/flake8-scrapy)

A [Flake8](https://flake8.pycqa.org/en/latest/) plugin to catch common issues
on Scrapy projects.

## Issue types

| Code  | Meaning |
| ---   | --- |
| SCP01 | There are URLs in `start_urls` whose netloc is not in `allowed_domains` |
| SCP02 | There are URLs in `allowed_domains` |
| SCP03 | Usage of `urljoin(response.url, '/foo')` instead of `response.urljoin('/foo')` |
| SCP04 | Usage of `Selector(response)` in callback |

This is a work in progress, so new issues will be added to this list.


## Installation

And then install flake8-scrapy:

```
$ pip install flake8-scrapy
```

Now, all you have to do is run it on your project:

```
$ flake8
```

And Flake8 will run the checks defined in this plugin.
