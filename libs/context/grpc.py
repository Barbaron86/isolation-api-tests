from grpc import ServicerContext

from libs.context.base import RequestContext


def get_grpc_request_context(context: ServicerContext) -> RequestContext:
    metadata = dict(context.invocation_metadata())
    return RequestContext(test_scenario=metadata.get("x-test-scenario"))


def build_grpc_metadata(context: RequestContext) -> list[tuple[str, str]]:
    metadata: list[tuple[str, str]] = []

    if context.test_scenario:
        metadata.append(("x-test-scenario", context.test_scenario))

    return metadata
