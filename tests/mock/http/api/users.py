import uuid
from http import HTTPStatus
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException

from tests.context.scenario import Scenario
from tests.mock.http.tools import get_scenario_http
from tests.schema.users import GetUserResponseTestSchema
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.tools.routes import APITestRoutes
from tests.types.gateway import GatewayTestErrorReason

# MockLoader — инфраструктурный компонент.
# Его ответственность строго ограничена:
# - загрузить мок-данные из файлов,
# - провалидировать их контрактом,
# - залогировать процесс загрузки.
#
# Loader не знает:
# - кто вызывает мок (gateway, тест, другой сервис),
# - зачем используется конкретный сценарий,
# - как устроена бизнес-логика системы.
loader = MockLoader(
    root=Path("./tests/mock/http/data/users"),
    logger=get_test_logger("USERS_SERVICE_MOCK_LOADER")
)

# Роутер представляет HTTP-контракт users-service.
# Префикс и пути соответствуют контрактам тестового стенда,
# а не внутренней реализации мок-сервиса.
users_mock_router = APIRouter(
    prefix=APITestRoutes.USERS,
    tags=[APITestRoutes.USERS]
)


@users_mock_router.get("/{user_id}", response_model=GetUserResponseTestSchema)
async def get_user_view(
        user_id: uuid.UUID,
        scenario: Scenario = Depends(get_scenario_http),
) -> GetUserResponseTestSchema:
    """Возвращает пользователя сценария только при совпадении запрошенного ID.

    Args:
        user_id: UUID из пути запроса к Users.
        scenario: Селектор набора данных из x-test-scenario.

    Returns:
        Подготовленный пользователь выбранного сценария.

    Raises:
        HTTPException: Со статусом 404, если сценарий не содержит запрошенного ID.
    """
    get_user_response_data = await loader.load_http(
        file=f"get_user/{scenario}.json",
        model=GetUserResponseTestSchema
    )
    if get_user_response_data.user.id != user_id:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND,
            detail=GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=user_id),
        )
    return get_user_response_data
