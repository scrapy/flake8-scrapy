from packaging.version import Version

from scrapy_lint.addons import Addon, VersionedSettings

SCRAPY_ZYTE_API_ADDON = Addon(
    package="scrapy-zyte-api",
    settings=VersionedSettings(
        history={
            Version("0.19.0"): {
                "DOWNLOAD_HANDLERS",
                "DOWNLOADER_MIDDLEWARES",
                "REQUEST_FINGERPRINTER_CLASS",
                "SCRAPY_POET_PROVIDERS",
                "SPIDER_MIDDLEWARES",
                "TWISTED_REACTOR",
                "ZYTE_API_TRANSPARENT_MODE",
                "ZYTE_API_FALLBACK_HTTP_HANDLER",
                "ZYTE_API_FALLBACK_HTTPS_HANDLER",
                "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
                "ZYTE_API_RETRY_POLICY",  # added
            },
            Version("0.17.3"): {
                "DOWNLOAD_HANDLERS",
                "DOWNLOADER_MIDDLEWARES",
                "REQUEST_FINGERPRINTER_CLASS",
                "SCRAPY_POET_PROVIDERS",  # added
                "SPIDER_MIDDLEWARES",
                "TWISTED_REACTOR",
                "ZYTE_API_TRANSPARENT_MODE",
                "ZYTE_API_FALLBACK_HTTP_HANDLER",
                "ZYTE_API_FALLBACK_HTTPS_HANDLER",
                "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
            },
            Version("0.17.0"): {
                "DOWNLOAD_HANDLERS",
                "DOWNLOADER_MIDDLEWARES",
                "REQUEST_FINGERPRINTER_CLASS",
                "SPIDER_MIDDLEWARES",
                "TWISTED_REACTOR",
                "ZYTE_API_TRANSPARENT_MODE",
                "ZYTE_API_FALLBACK_HTTP_HANDLER",
                "ZYTE_API_FALLBACK_HTTPS_HANDLER",
                "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
            },
        },
    ),
)


ADDONS = {
    "duplicate_url_discarder.Addon": Addon(
        package="duplicate-url-discarder",
        settings=VersionedSettings(
            history={
                Version("0.2.0"): {
                    "DUD_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
                    "ITEM_PIPELINES",  # added
                    "REQUEST_FINGERPRINTER_CLASS",
                },
                Version("0.1.0"): {
                    "DUD_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
                    "REQUEST_FINGERPRINTER_CLASS",
                },
            },
        ),
    ),
    "scrapy_poet.Addon": Addon(
        package="scrapy-poet",
        settings=VersionedSettings(
            settings={
                "DOWNLOADER_MIDDLEWARES",
                "REQUEST_FINGERPRINTER_CLASS",
                "SPIDER_MIDDLEWARES",
            },
        ),
    ),
    "scrapy_zyte_api.Addon": SCRAPY_ZYTE_API_ADDON,
    "scrapy_zyte_api.addon.Addon": SCRAPY_ZYTE_API_ADDON,
    "zyte_spider_templates.Addon": Addon(
        package="zyte-spider-templates",
        settings=VersionedSettings(
            settings={
                "CLOSESPIDER_TIMEOUT_NO_ITEM",
                "DOWNLOADER_MIDDLEWARES",
                "DUD_LOAD_RULE_PATHS",
                "ITEM_PROBABILITY_THRESHOLDS",
                "SCHEDULER_DISK_QUEUE",
                "SCHEDULER_MEMORY_QUEUE",
                "SCHEDULER_PRIORITY_QUEUE",
                "SCRAPY_POET_DISCOVER",
                "SPIDER_MIDDLEWARES",
                "SPIDER_MODULES",
            },
        ),
    ),
}
