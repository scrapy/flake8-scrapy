import scrapy


class URLINAllowedDomainsSpider(scrapy.Spider):
    """Sample that demonstrates the issue of having URLs
    in allowd_domains.
    """

    name = "url_not_in_allowed_domains"
    allowed_domains = [
        "http://example.com",
        "scrapy.org",
    ]
