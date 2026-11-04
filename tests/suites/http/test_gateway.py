from http import HTTPStatus
from uuid import UUID

import allure
import pytest

from tests.assertions.http.gateway import (
    assert_gateway_error_response,
    assert_gateway_not_found_response,
    assert_get_user_details_response_user_with_active_credit_card_account,
    assert_get_account_details_response_user_with_active_debit_card_account,
    assert_get_user_details_response_user_without_accounts,
    assert_get_account_details_response_account_without_cards,
)

from tests.clients.http.gateway.client import GatewayHTTPTestClient

from tests.context.base import RequestContext
from tests.context.scenario import Scenario

from tests.tools.allure import AllureTag, AllureStory, AllureFeature
from tests.types.gateway import GatewayTestErrorReason


@pytest.mark.gateway
@pytest.mark.regression
@allure.tag(AllureTag.HTTP, AllureTag.GATEWAY_SERVICE)
@allure.feature(AllureFeature.GATEWAY_SERVICE)
class TestGatewayHTTP:
    """Проверяет агрегаты Gateway через управляемые HTTP-моки."""

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. User with active credit card account")
    def test_get_user_details_user_with_active_credit_card_account(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            active_credit_account_user_id: UUID,
    ) -> None:
        """Проверяет пользователя и его кредитный счёт по явно запрошенному ID.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            active_credit_account_user_id: Ожидаемый ID пользователя сценария.
        """
        get_user_details_response_data = gateway_http_test_client.get_user_details(
            user_id=active_credit_account_user_id,
            context=RequestContext(
                scenario=Scenario.USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT
            ),
        )

        assert_get_user_details_response_user_with_active_credit_card_account(
            get_user_details_response_data,
            expected_user_id=active_credit_account_user_id,
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. User without accounts")
    def test_get_user_details_user_without_accounts(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            user_without_accounts_id: UUID,
    ) -> None:
        """Проверяет успешный ответ с пользователем и пустым списком счетов.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            user_without_accounts_id: ID существующего пользователя сценария.
        """
        get_user_details_response_data = gateway_http_test_client.get_user_details(
            user_id=user_without_accounts_id,
            context=RequestContext(scenario=Scenario.USER_WITHOUT_ACCOUNTS),
        )

        assert_get_user_details_response_user_without_accounts(
            get_user_details_response_data,
            expected_user_id=user_without_accounts_id,
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. User not found")
    def test_get_user_details_user_not_found(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            unknown_user_id: UUID,
    ) -> None:
        """Проверяет передачу Gateway ошибки Users с причиной и запрошенным ID.

        Users mock моделирует отсутствие пользователя ответом 404.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            unknown_user_id: Корректный UUID вне данных выбранного сценария.
        """
        get_user_details_response = gateway_http_test_client.get_user_details_api(
            user_id=unknown_user_id,
            context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT),
        )

        assert_gateway_not_found_response(
            get_user_details_response,
            expected_detail=GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=unknown_user_id),
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. User with active debit card account")
    def test_get_account_details_user_with_active_debit_card_account(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            active_debit_account_id: UUID,
    ) -> None:
        """Проверяет запрошенный дебетовый счёт и принадлежность обеих карт.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            active_debit_account_id: Ожидаемый ID счёта выбранного сценария.
        """
        get_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=active_debit_account_id,
            context=RequestContext(
                scenario=Scenario.USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT
            ),
        )

        assert_get_account_details_response_user_with_active_debit_card_account(
            get_account_details_response_data,
            expected_account_id=active_debit_account_id,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Account without cards")
    def test_get_account_details_account_without_cards(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            account_without_cards_id: UUID,
    ) -> None:
        """Проверяет успешный ответ со счётом и пустым списком карт.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            account_without_cards_id: ID существующего счёта сценария.
        """
        get_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=account_without_cards_id,
            context=RequestContext(scenario=Scenario.ACCOUNT_WITHOUT_CARDS),
        )

        assert_get_account_details_response_account_without_cards(
            get_account_details_response_data,
            expected_account_id=account_without_cards_id,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Account not found")
    def test_get_account_details_account_not_found(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            unknown_account_id: UUID,
    ) -> None:
        """Проверяет передачу Gateway ошибки Accounts с причиной и запрошенным ID.

        Accounts mock моделирует отсутствие счёта ответом 404.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            unknown_account_id: Корректный UUID вне данных выбранного сценария.
        """
        get_account_details_response = gateway_http_test_client.get_account_details_api(
            account_id=unknown_account_id,
            context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT),
        )

        assert_gateway_not_found_response(
            get_account_details_response,
            expected_detail=GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=unknown_account_id),
        )

    @pytest.mark.parametrize(
        "scenario,expected_detail",
        [
            pytest.param(
                Scenario.USERS_SERVICE_UNAVAILABLE,
                GatewayTestErrorReason.USERS_SERVICE_UNAVAILABLE,
                id="users-unavailable",
            ),
            pytest.param(
                Scenario.ACCOUNTS_LIST_UNAVAILABLE,
                GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE,
                id="accounts-list-unavailable",
            ),
        ],
    )
    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. Dependency unavailable: {scenario}")
    def test_get_user_details_dependency_unavailable(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            active_credit_account_user_id: UUID,
            scenario: Scenario,
            expected_detail: GatewayTestErrorReason,
    ) -> None:
        """Проверяет 503 и причину сбоя Users либо получения списка счетов.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            active_credit_account_user_id: ID подготовленного пользователя.
            scenario: Параметр, выбирающий сбой одной зависимости.
            expected_detail: Ожидаемая причина ошибки выбранного сервиса.
        """
        get_user_details_response = gateway_http_test_client.get_user_details_api(
            user_id=active_credit_account_user_id,
            context=RequestContext(scenario=scenario),
        )

        assert_gateway_error_response(
            get_user_details_response,
            expected_status=HTTPStatus.SERVICE_UNAVAILABLE,
            expected_detail=expected_detail,
        )

    @pytest.mark.parametrize(
        "scenario,expected_detail",
        [
            pytest.param(
                Scenario.CARDS_SERVICE_UNAVAILABLE,
                GatewayTestErrorReason.CARDS_SERVICE_UNAVAILABLE,
                id="cards-unavailable",
            ),
            pytest.param(
                Scenario.ACCOUNT_DETAILS_UNAVAILABLE,
                GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE,
                id="account-details-unavailable",
            ),
        ],
    )
    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Dependency unavailable: {scenario}")
    def test_get_account_details_dependency_unavailable(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            active_debit_account_id: UUID,
            scenario: Scenario,
            expected_detail: GatewayTestErrorReason,
    ) -> None:
        """Проверяет 503 и причину сбоя Cards либо получения самого счёта.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            active_debit_account_id: ID подготовленного счёта.
            scenario: Параметр, выбирающий сбой одной зависимости.
            expected_detail: Ожидаемая причина ошибки выбранного сервиса.
        """
        get_account_details_response = gateway_http_test_client.get_account_details_api(
            account_id=active_debit_account_id,
            context=RequestContext(scenario=scenario),
        )

        assert_gateway_error_response(
            get_account_details_response,
            expected_status=HTTPStatus.SERVICE_UNAVAILABLE,
            expected_detail=expected_detail,
        )
