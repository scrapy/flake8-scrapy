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


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ('response.css("*")[0].extract()', 1),
        ('response.xpath("//*")[0].extract()', 1),
        ('response.css("*").extract()[0]', 1),
        ('response.xpath("//*").extract()[0]', 1),
        ('response.css("*").getall()[0]', 1),
        ('response.xpath("//*")[0].get()', 1),
        ("selector.extract()", 0),
        ("selector[0].extract()", 0),
        ('response.jmespath("*")[0].extract()', 0),
        ('response.jmespath("*").extract()[0]', 0),
        ('response.css("*")[1].extract()', 0),
        ('response.css("*").extract()[1]', 0),
    ],
)
def test_find_oldstyle_get_first_by_index(code, expected):
    issues = run_checker(code)
    assert len(issues) == expected
