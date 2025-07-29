from packaging.version import Version

from scrapy_lint.packages import Package

PACKAGES = {
    "scrapy": Package(
        highest_known_version=Version("2.13.2"),
        lowest_safe_version=Version("2.11.2"),
        lowest_supported_version=Version("2.0.1"),
    ),
    "scrapy-crawlera": Package(
        replacements=("scrapy-zyte-smartproxy",),
    ),
    "scrapy-splash": Package(
        replacements=("scrapy-playwright", "scrapy-zyte-api"),
    ),
}
