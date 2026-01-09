from fastapi import Request

from libs.context.base import RequestContext


def get_http_request_context(request: Request) -> RequestContext:
    return RequestContext(test_scenario=request.headers.get("x-test-scenario"))
