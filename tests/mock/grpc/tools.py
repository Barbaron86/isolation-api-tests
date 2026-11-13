from grpc import StatusCode
from grpc.aio import ServicerContext
from redis.exceptions import ConnectionError as RedisConnectionError
from redis.exceptions import TimeoutError as RedisTimeoutError

from tests.context.scenario import Scenario
from tests.mock.scenarios import DynamicScenario, ScenarioStore


async def get_scenario_grpc(context: ServicerContext) -> Scenario:
    # В gRPC сценарий передаётся не через HTTP-заголовок,
    # а через metadata вызова.
    #
    # Это прямой архитектурный аналог X-Test-Scenario:
    # сценарий остаётся явным входом системы, просто на другом транспорте.

    metadata = dict(context.invocation_metadata())

    # В мок-сервисе мы используем единый ключ, согласованный со всем стендом:
    # x-test-scenario.
    #
    # Принципиально: мок не должен иметь дефолтного сценария,
    # иначе тесты перестают быть детерминированными и объяснимыми.
    raw = metadata.get("x-test-scenario")
    if not raw:
        # Отсутствие сценария — это ошибка клиента/теста.
        # Мы не продолжаем выполнение RPC и не возвращаем "пустой" ответ,
        # потому что такой ответ скрывает проблему в конфигурации.
        await context.abort(
            StatusCode.INVALID_ARGUMENT,
            "x-test-scenario metadata is required",
        )

    try:
        # Приводим строковое значение к доменному enum’у Scenario.
        # Это важная точка: сценарий должен быть валидным и известным системе.
        return Scenario(raw)
    except ValueError:
        # Неизвестный сценарий — та же категория ошибки, что и отсутствие.
        # Клиент передал значение, которого мок-сервис не понимает.
        await context.abort(
            StatusCode.INVALID_ARGUMENT,
            f"Unknown test scenario: {raw}",
        )


async def resolve_grpc_scenario(
    context: ServicerContext, scenario_store: ScenarioStore | None,
) -> Scenario | DynamicScenario:
    """Выбирает встроенный сценарий или читает динамический набор из Redis.

    Args:
        context: Контекст RPC с metadata x-test-scenario.
        scenario_store: Общее хранилище, если оно настроено для gRPC-мока.

    Returns:
        Имя встроенного сценария или сохранённые данные.

    Raises:
        grpc.aio.AbortError: При ошибочной metadata, отсутствии набора или
            недоступности хранилища.
    """
    scenario_id = dict(context.invocation_metadata()).get("x-test-scenario")
    if not scenario_id or not scenario_id.startswith("dynamic-") or scenario_id == "dynamic-":
        return await get_scenario_grpc(context)
    if scenario_store is None:
        await context.abort(StatusCode.UNAVAILABLE, "Mock scenario storage unavailable")
    try:
        scenario = await scenario_store.get(scenario_id)
    except (RedisConnectionError, RedisTimeoutError):
        await context.abort(StatusCode.UNAVAILABLE, "Mock scenario storage unavailable")
    if scenario is None:
        await context.abort(StatusCode.NOT_FOUND, f"Scenario {scenario_id} not found")
    return scenario
