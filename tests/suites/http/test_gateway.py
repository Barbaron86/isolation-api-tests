import allure
import pytest

# Доменные ассерты сценарного тестового слоя.
# Эти функции инкапсулируют бизнес-проверки ответа gateway
# и скрывают всю логику сравнения вложенных сущностей.
from tests.assertions.http.gateway import (
    assert_get_user_details_response_user_with_active_credit_card_account,
)

# HTTP API-клиент gateway-service тестового слоя.
# Клиент:
# - знает контракт gateway-service;
# - принимает RequestContext;
# - не содержит бизнес-логики и ассертов.
from tests.clients.http.gateway.client import GatewayHTTPTestClient

# RequestContext — формализованный способ управления внешним миром.
# Через него тест задаёт сценарий, который будет прокинут в HTTP-заголовки.
from tests.context.base import RequestContext
from tests.context.scenario import Scenario

# Семантические константы Allure.
# Они позволяют явно указать:
# - протокол (HTTP),
# - сервис (gateway),
# - бизнес-фичу и сценарий.
from tests.tools.allure import AllureTag, AllureStory, AllureFeature


# Pytest-маркеры уровня тестового набора.
#
# @pytest.mark.gateway — тесты gateway-service
# @pytest.mark.regression — регрессионный набор
#
# Эти маркеры используются для фильтрации запусков
# и CI/CD сценариев.
@pytest.mark.gateway
@pytest.mark.regression
# Allure-теги верхнего уровня.
#
# Здесь мы фиксируем:
# - что тест относится к HTTP-протоколу,
# - что тестирует gateway-service.
@allure.tag(AllureTag.HTTP, AllureTag.GATEWAY_SERVICE)
# Allure feature — бизнес-область теста.
# В отчёте Allure все тесты gateway будут сгруппированы вместе.
@allure.feature(AllureFeature.GATEWAY_SERVICE)
class TestGatewayHTTP:
    """
    Сценарные HTTP тесты gateway-service.

    Этот тестовый класс:
    - не подготавливает данные;
    - не управляет моками напрямую;
    - не содержит логики маршрутизации или агрегации.

    Он описывает сценарии взаимодействия с gateway
    в условиях полностью детерминированного внешнего мира.
    """

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. User with active credit card account")
    def test_get_user_details_user_with_active_credit_card_account(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
    ):
        """
        Сценарий:
        Пользователь с активным кредитным счётом
        запрашивает агрегированные данные через gateway-service.

        Управляющая переменная теста — сценарий.
        Все данные внешнего мира выбираются через него.
        """

        # Выполняем HTTP-вызов gateway-service.
        #
        # RequestContext явно задаёт сценарий:
        # USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT.
        #
        # Gateway-service не интерпретирует сценарий как бизнес-логику,
        # а просто прокидывает его в HTTP-интеграции,
        # где сценарий используется мок-сервисами.
        response = gateway_http_test_client.get_user_details(
            RequestContext(
                scenario=Scenario.USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT
            )
        )

        # Проверка результата выполняется доменным ассертoм.
        #
        # Ассерт:
        # - знает структуру ответа gateway;
        # - проверяет пользователя и его счета;
        # - использует фиксированный сценарный снапшот данных;
        # - формирует читаемый Allure-отчёт.
        #
        # Тест не сравнивает JSON, не перебирает поля
        # и не знает, откуда взялись ожидаемые данные.
        assert_get_user_details_response_user_with_active_credit_card_account(
            response
        )
