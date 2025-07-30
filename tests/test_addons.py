from packaging.version import Version

from scrapy_lint.data.addons import ADDONS


def test_all_time_settings():
    settings = ADDONS["scrapy_zyte_api.Addon"].settings
    assert settings.all_time_settings == {
        "DOWNLOADER_MIDDLEWARES",
        "DOWNLOAD_HANDLERS",
        "REQUEST_FINGERPRINTER_CLASS",
        "SPIDER_MIDDLEWARES",
        "TWISTED_REACTOR",
        "ZYTE_API_FALLBACK_HTTPS_HANDLER",
        "ZYTE_API_FALLBACK_HTTP_HANDLER",
        "ZYTE_API_FALLBACK_REQUEST_FINGERPRINTER_CLASS",
        "ZYTE_API_TRANSPARENT_MODE",
    }


def test_no_history():
    settings = ADDONS["scrapy_poet.Addon"].settings
    assert settings[Version("1.2.3")] == {
        "DOWNLOADER_MIDDLEWARES",
        "REQUEST_FINGERPRINTER_CLASS",
        "SPIDER_MIDDLEWARES",
    }
