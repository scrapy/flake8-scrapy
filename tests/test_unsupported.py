from __future__ import annotations

from typing import TYPE_CHECKING

from . import NO_ISSUE, Cases, ExpectedIssue, File, cases
from .helpers import check_project

if TYPE_CHECKING:
    from collections.abc import Sequence

ALL_REQUEST_CLASSES = (
    "Request",
    "scrapy.Request",
    "scrapy.http.Request",
    "http.Request",
    "scrapy.http.request.Request",
    "http.request.Request",
    "request.Request",
    "FormRequest",
    "scrapy.FormRequest",
    "scrapy.http.FormRequest",
    "http.FormRequest",
    "scrapy.http.request.form.FormRequest",
    "http.request.form.FormRequest",
    "request.form.FormRequest",
    "form.FormRequest",
    "JsonRequest",
    "scrapy.http.JsonRequest",
    "http.JsonRequest",
    "scrapy.http.request.json_request.JsonRequest",
    "http.request.json_request.JsonRequest",
    "request.json_request.JsonRequest",
    "json_request.JsonRequest",
    "XmlRpcRequest",
    "scrapy.http.XmlRpcRequest",
    "http.XmlRpcRequest",
    "scrapy.http.request.rpc.XmlRpcRequest",
    "http.request.rpc.XmlRpcRequest",
    "request.rpc.XmlRpcRequest",
    "rpc.XmlRpcRequest",
    "ScrapyRequest",
)
REPRESENTATIVE_REQUEST_CLASSES = (
    "Request",
    "scrapy.http.request.json_request.JsonRequest",
)
ALL_NON_REQUEST_CLASSES = (
    "foo.Request",
    # Long import paths should not trigger issues.
    "a.b.c.d.e.f.g.Request",
)

CASES: Cases = (
    *(
        (File(code, path=path), issues, {})
        for path in ("a.py",)
        for code, issues in (
            # All possible request classes are taken into account. Other
            # classes are ignored.
            *(
                (
                    f"{cls}(url, lambda x: x)",
                    ExpectedIssue(
                        "SCP05 lambda callback",
                        column=len(cls) + 6,
                        path=path,
                    ),
                )
                for cls in ALL_REQUEST_CLASSES
            ),
            *(
                (f"{cls}(url, lambda x: x)", NO_ISSUE)
                for cls in ALL_NON_REQUEST_CLASSES
            ),
            # No callback or errback params
            *((f"{cls}(url)", NO_ISSUE) for cls in REPRESENTATIVE_REQUEST_CLASSES),
            # Combinations of callback and errback params using pairwise testing
            *(
                (
                    f"{cls}(url, {callback_prefix}{callback}, {errback_prefix}{errback})",
                    [*callback_issues, *errback_issues],
                )
                for cls in REPRESENTATIVE_REQUEST_CLASSES
                for callback_prefix, errback_prefix in (
                    ("", "errback="),
                    ("callback=", "errback="),
                    ("", "'GET', None, None, None, None, 'utf-8', 0, False, "),
                )
                for callback, callback_issues, errback, errback_issues in (
                    # Lambda callback with non-lambda errback
                    (
                        "lambda x: x",
                        [
                            ExpectedIssue(
                                "SCP05 lambda callback",
                                column=len(cls) + len(callback_prefix) + 6,
                                path=path,
                            ),
                        ],
                        "foo",
                        [],
                    ),
                    # Non-lambda callback with lambda errback
                    (
                        "foo",
                        [],
                        "lambda x: x",
                        [
                            ExpectedIssue(
                                "SCP05 lambda callback",
                                column=len(cls)
                                + len(callback_prefix)
                                + len("foo")
                                + len(errback_prefix)
                                + 8,
                                path=path,
                            ),
                        ],
                    ),
                    # Both lambda
                    (
                        "lambda x: x",
                        [
                            ExpectedIssue(
                                "SCP05 lambda callback",
                                column=len(cls) + len(callback_prefix) + 6,
                                path=path,
                            ),
                        ],
                        "lambda x: x",
                        [
                            ExpectedIssue(
                                "SCP05 lambda callback",
                                column=len(cls)
                                + len(callback_prefix)
                                + len("lambda x: x")
                                + len(errback_prefix)
                                + 8,
                                path=path,
                            ),
                        ],
                    ),
                    # Representative non-lambda cases
                    ("foo", [], "None", []),
                    ("'foo'", [], "self.foo", []),
                    ("None", [], "scrapy.http.request.NO_CALLBACK", []),
                )
            ),
            # Classes with an import path including attribute objects with a
            # value that is neither a Name nor an Attribute, e.g. a Subscript,
            # are ignored.
            ("a[0].Request(url, callback=lambda x: x)", NO_ISSUE),
            ("a[0].b.Request(url, callback=lambda x: x)", NO_ISSUE),
            # Lambda assignments to callback/errback attributes
            (
                "a.callback = lambda x: x",
                ExpectedIssue("SCP05 lambda callback", column=13, path=path),
            ),
            (
                "a.errback = lambda x: x",
                ExpectedIssue("SCP05 lambda callback", column=12, path=path),
            ),
            (
                "request.callback = lambda x: x",
                ExpectedIssue("SCP05 lambda callback", column=19, path=path),
            ),
            (
                "request.errback = lambda x: x",
                ExpectedIssue("SCP05 lambda callback", column=18, path=path),
            ),
            # Multiple targets in assignment (though rare, should still be detected)
            (
                "obj.callback = other.callback = lambda x: x",
                ExpectedIssue("SCP05 lambda callback", column=32, path=path),
            ),
            # Non-lambda assignments to callback/errback attributes (should not trigger)
            ("obj.callback = some_function", NO_ISSUE),
            ("obj.errback = self.handle_error", NO_ISSUE),
            ("request.callback = None", NO_ISSUE),
            ("request.errback = 'error_handler'", NO_ISSUE),
            # Lambda assignments to other attributes (should not trigger)
            ("obj.other_attr = lambda x: x", NO_ISSUE),
            ("request.parser = lambda x: x", NO_ISSUE),
            # Non-attribute assignments with lambda (should not trigger)
            ("callback = lambda x: x", NO_ISSUE),
            ("errback = lambda x: x", NO_ISSUE),
            # Request.replace() calls with lambda callbacks/errbacks
            (
                "request.replace(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=25, path=path),
            ),
            (
                "request.replace(errback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=24, path=path),
            ),
            (
                "req.replace(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=21, path=path),
            ),
            (
                "self.request.replace(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=30, path=path),
            ),
            # replace() with positional lambda arguments
            (
                "request.replace(url, lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=21, path=path),
            ),
            # replace() with both callback and errback lambdas
            (
                "request.replace(callback=lambda x: x, errback=lambda y: y)",
                [
                    ExpectedIssue("SCP05 lambda callback", column=25, path=path),
                    ExpectedIssue("SCP05 lambda callback", column=46, path=path),
                ],
            ),
            # replace() with non-lambda callbacks (should not trigger)
            ("request.replace(callback=self.parse)", NO_ISSUE),
            ("request.replace(errback=self.error_handler)", NO_ISSUE),
            ("request.replace(callback=None)", NO_ISSUE),
            # replace() on other objects with lambda (pragmatic approach - should trigger)
            (
                "obj.replace(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=21, path=path),
            ),
            (
                "string_obj.replace(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=28, path=path),
            ),
            # replace() with other parameters and lambda
            (
                "request.replace(url='new_url', callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=40, path=path),
            ),
            # Response.follow() calls with lambda callbacks/errbacks
            (
                "response.follow(url, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=30, path=path),
            ),
            (
                "response.follow(url, errback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=29, path=path),
            ),
            (
                "response.follow(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=25, path=path),
            ),
            (
                "self.response.follow(url, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=35, path=path),
            ),
            # Response.follow_all() calls with lambda callbacks/errbacks
            (
                "response.follow_all(urls, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=35, path=path),
            ),
            (
                "response.follow_all(urls, errback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=34, path=path),
            ),
            (
                "response.follow_all(callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=29, path=path),
            ),
            # follow() with both callback and errback lambdas
            (
                "response.follow(url, callback=lambda x: x, errback=lambda y: y)",
                [
                    ExpectedIssue("SCP05 lambda callback", column=30, path=path),
                    ExpectedIssue("SCP05 lambda callback", column=51, path=path),
                ],
            ),
            # follow_all() with both callback and errback lambdas
            (
                "response.follow_all(urls, callback=lambda x: x, errback=lambda y: y)",
                [
                    ExpectedIssue("SCP05 lambda callback", column=35, path=path),
                    ExpectedIssue("SCP05 lambda callback", column=56, path=path),
                ],
            ),
            # follow() with non-lambda callbacks (should not trigger)
            ("response.follow(url, callback=self.parse)", NO_ISSUE),
            ("response.follow(url, errback=self.error_handler)", NO_ISSUE),
            ("response.follow_all(urls, callback=None)", NO_ISSUE),
            # follow() on other objects with lambda (pragmatic approach - should trigger)
            (
                "obj.follow(url, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=25, path=path),
            ),
            (
                "other_obj.follow_all(items, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=37, path=path),
            ),
            # FormRequest.from_response() calls with lambda callbacks/errbacks (keyword-only)
            (
                "FormRequest.from_response(response, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=45, path=path),
            ),
            (
                "FormRequest.from_response(response, errback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=44, path=path),
            ),
            (
                "scrapy.FormRequest.from_response(response, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=52, path=path),
            ),
            (
                "self.FormRequest.from_response(response, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=50, path=path),
            ),
            # from_response() with both callback and errback lambdas
            (
                "FormRequest.from_response(response, callback=lambda x: x, errback=lambda y: y)",
                [
                    ExpectedIssue("SCP05 lambda callback", column=45, path=path),
                    ExpectedIssue("SCP05 lambda callback", column=66, path=path),
                ],
            ),
            # from_response() with form data and lambda callback
            (
                "FormRequest.from_response(response, formdata={'key': 'value'}, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=72, path=path),
            ),
            # from_response() with non-lambda callbacks (should not trigger)
            ("FormRequest.from_response(response, callback=self.parse)", NO_ISSUE),
            (
                "FormRequest.from_response(response, errback=self.error_handler)",
                NO_ISSUE,
            ),
            ("FormRequest.from_response(response, callback=None)", NO_ISSUE),
            # from_response() on other objects with lambda (pragmatic approach - should trigger)
            (
                "obj.from_response(response, callback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=37, path=path),
            ),
            (
                "CustomRequest.from_response(response, errback=lambda x: x)",
                ExpectedIssue("SCP05 lambda callback", column=46, path=path),
            ),
            # from_response() without callback/errback keywords should not trigger
            ("FormRequest.from_response(response)", NO_ISSUE),
            (
                "FormRequest.from_response(response, formdata={'key': 'value'})",
                NO_ISSUE,
            ),
        )
    ),
)


@cases(CASES)
def test(
    files: File | Sequence[File],
    expected: ExpectedIssue | Sequence[ExpectedIssue] | None,
    options,
):
    check_project(files, expected, options)
