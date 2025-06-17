import pytest

from flake8_scrapy.finders.oldstyle import UrlJoinIssueFinder

from . import run_checker


@pytest.mark.parametrize(
    "code",
    [
        ('urljoin(response.url, "/foo")'),
        ('url = urljoin(response.url, "/foo")'),
    ],
)
def test_finds_old_style_urljoin(code):
    issues = run_checker(code)
    assert len(issues) == 1
    assert UrlJoinIssueFinder.msg_code in issues[0][2]


@pytest.mark.parametrize(
    "code",
    [
        ('response.urljoin("/foo")'),
        ("url = urljoin()"),
        ('urljoin(x, "/foo")'),
        ('urljoin(x.y.z, "/foo")'),
    ],
)
def test_dont_find_old_style_urljoin(code):
    issues = run_checker(code)
    assert len(issues) == 0


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("sel = Selector(response)", 1),
        ('sel = Selector(response, type="html")', 1),
        ('sel = Selector(response=response, type="html")', 1),
        ("sel = Selector(response=response)", 1),
        ("sel = Selector(text=response.text)", 1),
        ("sel = Selector(text=response.body)", 1),
        ("sel = Selector(text=response.body_as_unicode())", 1),
        ('sel = Selector(text=response.text, type="html")', 1),
        ("sel = Selector(get_text())", 0),
        ("sel = Selector(self.get_text())", 0),
    ],
)
def test_find_old_style_selector(code, expected):
    issues = run_checker(code)
    assert len(issues) == expected
