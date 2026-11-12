from pydantic import BaseModel, Field

from tests.context.scenario import Scenario


class RequestContext(BaseModel):
    """
    Единый контекст запроса для тестового слоя.

    Контекст — это способ передать в запрос не только "данные запроса",
    но и управляющую информацию о том, какой внешний мир должен быть
    смоделирован моками.

    Сейчас в контексте есть только scenario, но сущность введена
    заранее, потому что в будущем контекст может расширяться:
    trace_id, дополнительные ключи маршрутизации моков и т.д.
    """
    scenario: Scenario


class DynamicHTTPRequestContext(BaseModel):
    """Передаёт ID сценария, зарегистрированного через HTTP Admin API мока."""

    scenario: str = Field(pattern=r"^dynamic-.+$")


def build_grpc_test_metadata(context: RequestContext) -> list[tuple[str, str]]:
    """
    Преобразует RequestContext в gRPC metadata.

    gRPC не использует HTTP-заголовки напрямую, но смысл тот же:
    передать управляющий контекст на транспортный уровень,
    чтобы его могли прочитать downstream-интеграции и mock-сервер.
    """
    return [("x-test-scenario", context.scenario)]


def build_http_test_headers(context: RequestContext | DynamicHTTPRequestContext) -> dict[str, str]:
    """Формирует HTTP-заголовок для выбора встроенного или динамического сценария.

    Args:
        context: Контекст с именем встроенного сценария или ID регистрации.

    Returns:
        Заголовок X-Test-Scenario с выбранным значением.
    """
    return {"x-test-scenario": context.scenario}
