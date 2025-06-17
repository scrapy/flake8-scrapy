import ast
from pathlib import Path

from flake8_scrapy import ScrapyStyleChecker


def load_sample_file(filename):
    return (Path(__file__).parent / "samples" / filename).read_text()


def run_checker(code):
    tree = ast.parse(code)
    checker = ScrapyStyleChecker(tree, None)
    return list(checker.run())
