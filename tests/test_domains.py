from finders.domains import (
    UnreachableDomainIssueFinder,
    UrlInAllowedDomainsIssueFinder,
)

from . import load_sample_file, run_checker


def test_url_not_in_allowed_domains():
    code = load_sample_file("allowed_domains.py")
    issues = run_checker(code)

    assert len(issues) == 2
    # first issue
    assert issues[0][0] == 15  # line
    assert issues[0][1] == 8  # col
    assert UnreachableDomainIssueFinder.msg_code in issues[0][2]
    assert UnreachableDomainIssueFinder.msg_info in issues[0][2]
    # second issue
    assert issues[1][0] == 16  # line
    assert issues[1][1] == 8  # col
    assert UnreachableDomainIssueFinder.msg_code in issues[1][2]
    assert UnreachableDomainIssueFinder.msg_info in issues[1][2]


def test_url_in_allowed_domains():
    code = load_sample_file("url_in_allowed_domains.py")
    issues = run_checker(code)

    assert len(issues) == 1
    assert issues[0][0] == 11  # line
    assert issues[0][1] == 8  # col
    assert UrlInAllowedDomainsIssueFinder.msg_code in issues[0][2]
    assert UrlInAllowedDomainsIssueFinder.msg_info in issues[0][2]
