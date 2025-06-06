import ast
import os

from flake8_scrapy import ScrapyStyleChecker


def load_sample_file(filename):
    path = os.path.join(os.path.dirname(__file__), "samples", filename)
    return open(path).read()


def run_checker(code):
    tree = ast.parse(code)
    checker = ScrapyStyleChecker(tree, None)
    return list(checker.run())
