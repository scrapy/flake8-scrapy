from packaging.utils import canonicalize_name
from packaging.version import Version

from flake8_scrapy.data.packages import PACKAGES
from flake8_scrapy.finders.requirements import RequirementsIssueFinder

from . import NO_ISSUE, Cases, File, Issue, cases
from .helpers import check_project

SCRAPY_FUTURE_VERSION = Version("3.0.0")
SCRAPY_HIGHEST_KNOWN = PACKAGES["scrapy"].highest_known_version
SCRAPY_LOWEST_SAFE = PACKAGES["scrapy"].lowest_safe_version
SCRAPY_INSECURE_VERSION = Version("2.11.1")
SCRAPY_LOWEST_SUPPORTED = PACKAGES["scrapy"].lowest_supported_version
SCRAPY_ANCIENT_VERSION = Version("2.0.0")

CASES: Cases = (
    # No scrapy.cfg file
    ((File("", path="requirements.txt"),), NO_ISSUE, {}),
    # Non-standard requirements file name
    (
        (File("", path="scrapy.cfg"), File("", path="requirements-dev.txt")),
        NO_ISSUE,
        {},
    ),
    # SCP13 incomplete requirement freeze
    *(
        ((File("", path="scrapy.cfg"), File(requirements, path=path)), issues, {})
        for path in ("requirements.txt",)
        for requirements, issues in (
            *(
                (requirements, NO_ISSUE)
                for requirements in (
                    # All required dependencies with standard package names
                    "\n".join(
                        [
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service-identity==23.1.0",
                            "Twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                        ]
                    ),
                    # Different package name formats (service_identity vs
                    # service-identity, twisted vs Twisted)
                    "\n".join(
                        [
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service_identity==23.1.0",
                            "twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                        ]
                    ),
                    # All required dependencies plus extra packages
                    "\n".join(
                        [
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                            "requests==2.31.0",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                            "protego==0.3.0",
                            "pyOpenSSL==23.2.0",
                            "queuelib==1.7.0",
                            "service-identity==23.1.0",
                            "Twisted==23.8.0",
                            "w3lib==2.1.2",
                            "zope.interface==6.0",
                        ]
                    ),
                )
            ),
            *(
                (requirements, Issue("SCP13 incomplete requirements freeze", path=path))
                for requirements in (
                    # Empty requirements file
                    "",
                    # Only comments in requirements file
                    "\n".join(["# This is a comment", "# Another comment"]),
                    # Editable install (not frozen)
                    "-e git+https://github.com/scrapy/scrapy.git#egg=scrapy",
                    # Missing most required dependencies
                    "\n".join([f"scrapy=={SCRAPY_HIGHEST_KNOWN}", "requests==2.31.0"]),
                    # Missing some required dependencies
                    "\n".join(
                        [
                            f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                            "cryptography==41.0.4",
                            "cssselect==1.2.0",
                            "lxml==4.9.3",
                            "parsel==1.8.1",
                        ]
                    ),
                )
            ),
        )
    ),
    # SCP24 missing stack requirements
    *(
        (
            (
                File("", path="scrapy.cfg"),
                File("image: custom:latest", path="scrapinghub.yml"),
                File(requirements, path=path),
            ),
            issues,
            {},
        )
        for path in ("requirements.txt",)
        for requirements, issues in (
            # All stack dependencies present
            (
                "\n".join(
                    [
                        "aiohttp==3.8.4",
                        "awscli==1.29.0",
                        "boto==2.49.0",
                        "boto3==1.28.0",
                        "jinja2==3.1.2",
                        "lxml==4.9.3",
                        "monkeylearn==3.5.0",
                        "pillow==10.0.0",
                        "pyyaml==6.0.1",
                        "requests==2.31.0",
                        "scrapinghub==2.4.0",
                        "scrapinghub-entrypoint-scrapy==0.12.0",
                        f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                        "scrapy-deltafetch==2.0.1",
                        "scrapy-dotpersistence==0.3.0",
                        "scrapy-magicfields==1.1.0",
                        "scrapy-pagestorage==0.2.3",
                        "scrapy-querycleaner==0.1.0",
                        "scrapy-splitvariants==0.1.0",
                        "scrapy-zyte-smartproxy==2.1.0",
                        "spidermon==1.20.0",
                        "twisted==23.8.0",
                        "urllib3==2.0.4",
                        "cryptography==41.0.4",
                        "cssselect==1.2.0",
                        "parsel==1.8.1",
                        "protego==0.3.0",
                        "pyOpenSSL==23.2.0",
                        "queuelib==1.7.0",
                        "service-identity==23.1.0",
                        "w3lib==2.1.2",
                        "zope.interface==6.0",
                    ]
                ),
                NO_ISSUE,
            ),
            # Missing some stack dependencies
            (
                "\n".join(
                    [
                        f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                        "requests==2.31.0",
                        "lxml==4.9.3",
                        "cryptography==41.0.4",
                        "cssselect==1.2.0",
                        "parsel==1.8.1",
                        "protego==0.3.0",
                        "pyOpenSSL==23.2.0",
                        "queuelib==1.7.0",
                        "service-identity==23.1.0",
                        "twisted==23.8.0",
                        "w3lib==2.1.2",
                        "zope.interface==6.0",
                    ]
                ),
                (
                    Issue(
                        "SCP24 missing stack requirements: missing packages: aiohttp, awscli, boto, boto3, jinja2, monkeylearn, pillow, pyyaml, scrapinghub, scrapinghub-entrypoint-scrapy, scrapy-deltafetch, scrapy-dotpersistence, scrapy-magicfields, scrapy-pagestorage, scrapy-querycleaner, scrapy-splitvariants, scrapy-zyte-smartproxy, spidermon, urllib3",
                        path=path,
                    ),
                ),
            ),
            # Empty requirements file with scrapinghub.yml
            (
                "",
                (
                    Issue("SCP13 incomplete requirements freeze", path=path),
                    Issue(
                        "SCP24 missing stack requirements: missing packages: aiohttp, awscli, boto, boto3, jinja2, monkeylearn, pillow, pyyaml, requests, scrapinghub, scrapinghub-entrypoint-scrapy, scrapy-deltafetch, scrapy-dotpersistence, scrapy-magicfields, scrapy-pagestorage, scrapy-querycleaner, scrapy-splitvariants, scrapy-zyte-smartproxy, spidermon, urllib3",
                        path=path,
                    ),
                ),
            ),
        )
    ),
    # SCP24 should not trigger without scrapinghub.yml
    *(
        ((File("", path="scrapy.cfg"), File(requirements, path=path)), issues, {})
        for path in ("requirements.txt",)
        for requirements, issues in (
            # Missing stack dependencies but no scrapinghub.yml
            (
                "\n".join(
                    [
                        f"scrapy=={SCRAPY_HIGHEST_KNOWN}",
                        "requests==2.31.0",
                    ]
                ),
                (Issue("SCP13 incomplete requirements freeze", path=path),),
            ),
        )
    ),
    # Tests for specific requirements
    *(
        (
            (File("", path="scrapy.cfg"), File(requirements, path=path)),
            (Issue("SCP13 incomplete requirements freeze", path=path), *issues),
            {},
        )
        for path in ("requirements.txt",)
        for requirements, issues in (
            # SCP14 unsupported requirement
            # SCP15 insecure requirement
            *(
                (f"scrapy=={version}", issues)
                for version, issues in (
                    (SCRAPY_FUTURE_VERSION, ()),
                    (SCRAPY_HIGHEST_KNOWN, ()),
                    (SCRAPY_LOWEST_SAFE, ()),
                    (
                        SCRAPY_INSECURE_VERSION,
                        (
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                    (
                        SCRAPY_LOWEST_SUPPORTED,
                        (
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                    (
                        SCRAPY_ANCIENT_VERSION,
                        (
                            Issue(
                                f"SCP14 unsupported requirement: scrapy-flake8 only supports scrapy>={SCRAPY_LOWEST_SUPPORTED}+",
                                path=path,
                            ),
                            Issue(
                                f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                                path=path,
                            ),
                        ),
                    ),
                )
            ),
            # Non-frozen versions should not trigger SCP14/SCP15
            *(
                (requirements, ())
                for requirements in (
                    f"scrapy>={SCRAPY_ANCIENT_VERSION}",  # Ancient but not frozen
                    f"scrapy~={SCRAPY_INSECURE_VERSION}",  # Insecure but not frozen
                    f"scrapy!={SCRAPY_ANCIENT_VERSION}",  # Ancient but not frozen
                    "scrapy>=2.0.0,<3.0.0",  # Range specification
                )
            ),
            # Invalid versions should not trigger SCP14/SCP15
            ("scrapy==latest", ()),
            ("scrapy==1.0.0-beta.1.5", ()),
            ("scrapy==1.0.0-alpha..1", ()),
            # SCP16 unmaintained packages
            (
                "scrapy-crawlera",
                (
                    Issue(
                        "SCP16 unmaintained requirement: replace with scrapy-zyte-smartproxy",
                        path=path,
                    ),
                ),
            ),
            (
                "scrapy-splash==1.2.3",
                (
                    Issue(
                        "SCP16 unmaintained requirement: replace with one of: scrapy-playwright, scrapy-zyte-api",
                        path=path,
                    ),
                ),
            ),
            # Signs of SCP13, like editable installs (-e), should not prevent
            # the reporting of SCP14/SCP15/SCP16.
            (
                "\n".join(
                    [
                        "-e git+https://github.com/scrapy/parsel.git#egg=parsel",
                        f"scrapy=={SCRAPY_ANCIENT_VERSION}",
                        "scrapy-crawlera~=1.0.0",
                    ]
                ),
                (
                    Issue(
                        f"SCP14 unsupported requirement: scrapy-flake8 only supports scrapy>={SCRAPY_LOWEST_SUPPORTED}+",
                        line=2,
                        path=path,
                    ),
                    Issue(
                        f"SCP15 insecure requirement: scrapy {SCRAPY_LOWEST_SAFE} implements security fixes",
                        line=2,
                        path=path,
                    ),
                    Issue(
                        "SCP16 unmaintained requirement: replace with scrapy-zyte-smartproxy",
                        line=3,
                        path=path,
                    ),
                ),
            ),
        )
    ),
)


@cases(CASES)
def test(input, expected, flake8_options):
    check_project(input, expected, flake8_options)


def test_required_dependencies_are_canonical():
    deps = set(RequirementsIssueFinder.REQUIRED_DEPENDENCIES) | set(
        RequirementsIssueFinder.SCRAPY_CLOUD_STACK_DEPENDENCIES
    )
    for dep in set(deps):
        assert dep == canonicalize_name(dep)


def test_version_constants():
    assert SCRAPY_HIGHEST_KNOWN is not None
    assert SCRAPY_LOWEST_SAFE is not None
    assert SCRAPY_LOWEST_SUPPORTED is not None

    assert SCRAPY_FUTURE_VERSION >= SCRAPY_HIGHEST_KNOWN
    assert SCRAPY_HIGHEST_KNOWN >= SCRAPY_LOWEST_SAFE
    assert SCRAPY_LOWEST_SAFE >= SCRAPY_INSECURE_VERSION
    assert SCRAPY_INSECURE_VERSION >= SCRAPY_LOWEST_SUPPORTED
    assert SCRAPY_LOWEST_SUPPORTED >= SCRAPY_ANCIENT_VERSION
