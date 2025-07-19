import ast
from collections.abc import Generator
from urllib.parse import urlparse

from flake8_scrapy.issues import DISALLOWED_DOMAIN, URL_IN_ALLOWED_DOMAINS, Issue, Pos

from . import IssueFinder


def get_list_metadata(node):
    return [
        (subnode.lineno, subnode.col_offset, subnode.value)
        for subnode in node.value.elts
        if isinstance(subnode, ast.Constant)
    ]


def is_list_assignment(node, var_name):
    return (
        isinstance(node.targets[0], ast.Name)
        and isinstance(node.value, (ast.List, ast.Tuple))
        and node.targets[0].id == var_name
    )


class UnreachableDomainIssueFinder(IssueFinder):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.allowed_domains = []
        self.start_urls = []

    def url_in_allowed_domains(self, url):
        netloc = urlparse(url).netloc
        return any(domain in netloc for _, _, domain in self.allowed_domains)

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if is_list_assignment(node, var_name="allowed_domains"):
            self.allowed_domains = get_list_metadata(node)

        if is_list_assignment(node, var_name="start_urls"):
            self.start_urls = get_list_metadata(node)

        if not all((self.allowed_domains, self.start_urls)):
            return

        for line, column, url in self.start_urls:
            if not self.url_in_allowed_domains(url):
                yield Issue(DISALLOWED_DOMAIN, Pos(line, column))


class UrlInAllowedDomainsIssueFinder(IssueFinder):
    def is_url(self, domain):
        # when it's just a domain (as 'toscrape.com'), the parsed URL contains
        # only the 'path' component
        forbidden_components = [
            "scheme",
            "netloc",
            "params",
            "query",
            "fragment",
        ]
        parts = urlparse(domain)
        return any(getattr(parts, comp, None) for comp in forbidden_components)

    def find_issues(self, node) -> Generator[Issue, None, None]:
        if is_list_assignment(node, var_name="allowed_domains"):
            allowed_domains = get_list_metadata(node)

            for line, column, url in allowed_domains:
                if self.is_url(url):
                    yield Issue(URL_IN_ALLOWED_DOMAINS, Pos(line, column))
