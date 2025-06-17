import ast

from .finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)
from .finders.oldstyle import (
    ExtractThenIndexIssueFinder,
    GetFirstByIndexIssueFinder,
    OldSelectorIssueFinder,
    UrlJoinIssueFinder,
)
from .finders.unsupported import LambdaCallbackIssueFinder

__version__ = "0.0.2"


class ScrapyStyleIssueFinder(ast.NodeVisitor):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.issues = []
        lambda_callback_issue_finder = LambdaCallbackIssueFinder()
        self.finders = {
            "Assign": [
                UnreachableDomainIssueFinder(),
                UrlInAllowedDomainsIssueFinder(),
                OldSelectorIssueFinder(),
                lambda_callback_issue_finder,
            ],
            "Call": [
                GetFirstByIndexIssueFinder(),
                UrlJoinIssueFinder(),
                lambda_callback_issue_finder,
            ],
            "Subscript": [
                ExtractThenIndexIssueFinder(),
            ],
        }

    def find_issues_visitor(self, visitor, node):
        """Find issues for the provided visitor"""
        for finder in self.finders[visitor]:
            issues = finder.find_issues(node)
            if issues:
                self.issues.extend(list(issues))
        self.generic_visit(node)

    def visit_Assign(self, node):
        self.find_issues_visitor("Assign", node)

    def visit_Call(self, node):
        self.find_issues_visitor("Call", node)

    def visit_Subscript(self, node):
        self.find_issues_visitor("Subscript", node)


class ScrapyStyleChecker:
    options = None
    name = "flake8-scrapy"
    version = __version__

    def __init__(self, tree, filename):
        self.tree = tree
        self.filename = filename

    def run(self):
        finder = ScrapyStyleIssueFinder()
        finder.visit(self.tree)

        for line, col, msg in finder.issues:
            yield (line, col, msg, ScrapyStyleChecker)
