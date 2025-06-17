import scrapy


class AllowedDomainsSpider(scrapy.Spider):
    """Sample that demonstrates the issue of having start_urls
    for domains out of allowed_domains.
    """

    # name = 'allowed_domains'
    allowed_domains = (
        "example.com",
        "scrapy.org",
    )
    start_urls = [  # noqa: RUF012
        "http://quotes.toscrape.com",
        "http://httpbin.org",
    ]

    def parse(self, response):
        self.do_nothing()

    def do_nothing(self):
        pass
