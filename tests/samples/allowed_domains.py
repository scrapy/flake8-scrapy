import scrapy


class AllowedDomainsSpider(scrapy.Spider):
    """Sample that demonstrates the issue of having start_urls
    for domains out of allowed_domains.
    """

    # name = 'allowed_domains'
    allowed_domains = (
        "a.example",
        "b.example",
    )
    start_urls = [  # noqa: RUF012
        "https://c.example",
        "https://d.example",
    ]

    def parse(self, response):
        self.do_nothing()

    def do_nothing(self):
        pass
