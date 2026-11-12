from collections.abc import Callable
from http import HTTPStatus
from uuid import UUID, uuid4

import allure
import pytest
from httpx import QueryParams

from tests.assertions.base import assert_equal
from tests.assertions.http.base import assert_status_code
from tests.assertions.http.gateway import (
    assert_gateway_error_response,
    assert_gateway_not_found_response,
    assert_get_account_details_response,
    assert_get_user_details_response,
)

from tests.clients.http.gateway.client import GatewayHTTPTestClient
from tests.clients.http.mock_admin import build_mock_admin_http_test_client

from tests.context.base import DynamicHTTPRequestContext, RequestContext
from tests.context.scenario import Scenario

from tests.schema.cards import GetCardsResponseTestSchema
from tests.schema.gateway import (
    AccountDetailsTestSchema,
    GetAccountDetailsResponseTestSchema,
    GetUserDetailsResponseTestSchema,
    UserDetailsTestSchema,
)
from tests.schema.mock_gateway import GatewayMockOperation, GatewayMockScenarioTestSchema
from tests.tools.allure import AllureTag, AllureStory, AllureFeature
from tests.tools.gateway_data import make_account, make_card, make_user
from tests.tools.gateway_expectations import (
    expected_account_details,
    expected_account_details_with_mixed_cards,
    expected_account_details_without_cards,
    expected_active_credit_user_details,
    expected_active_debit_account_details,
    expected_user_details,
    expected_user_details_with_multiple_accounts,
    expected_user_details_without_accounts,
)
from tests.tools.routes import APITestRoutes
from tests.types.accounts import AccountTestType
from tests.types.cards import CardTestPaymentSystem, CardTestType
from tests.types.gateway import GatewayTestErrorReason


@pytest.mark.gateway
@pytest.mark.regression
@allure.tag(AllureTag.HTTP, AllureTag.GATEWAY_SERVICE)
@allure.feature(AllureFeature.GATEWAY_SERVICE)
class TestGatewayHTTP:
    """Проверяет агрегаты и ошибки Gateway на встроенных JSON-сценариях."""

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

        assert_get_user_details_response(
            get_user_details_response_data,
            expected=expected_active_credit_user_details(user_id=active_credit_account_user_id),
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

        assert_get_user_details_response(
            get_user_details_response_data,
            expected=expected_user_details_without_accounts(user_id=user_without_accounts_id),
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. User with multiple accounts")
    def test_get_user_details_user_with_multiple_accounts(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            user_with_multiple_accounts_id: UUID,
    ) -> None:
        """Проверяет оба счёта пользователя и исключение счёта другого владельца.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            user_with_multiple_accounts_id: ID владельца двух подготовленных счетов.
        """
        get_user_details_response_data = gateway_http_test_client.get_user_details(
            user_id=user_with_multiple_accounts_id,
            context=RequestContext(scenario=Scenario.USER_WITH_MULTIPLE_ACCOUNTS),
        )

        assert_get_user_details_response(
            get_user_details_response_data,
            expected=expected_user_details_with_multiple_accounts(user_id=user_with_multiple_accounts_id),
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

        assert_get_account_details_response(
            get_account_details_response_data,
            expected=expected_active_debit_account_details(account_id=active_debit_account_id),
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

        assert_get_account_details_response(
            get_account_details_response_data,
            expected=expected_account_details_without_cards(account_id=account_without_cards_id),
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Cards belong to requested account")
    def test_get_account_details_cards_belong_to_account(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            account_with_mixed_cards_id: UUID,
            user_with_multiple_accounts_id: UUID,
    ) -> None:
        """Проверяет две карты запрошенного счёта и исключение карты другого счёта.

        Args:
            gateway_http_test_client: Фикстура клиента Gateway HTTP API.
            account_with_mixed_cards_id: ID подготовленного дебетового счёта.
            user_with_multiple_accounts_id: ID владельца подготовленного счёта.
        """
        get_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=account_with_mixed_cards_id,
            context=RequestContext(scenario=Scenario.ACCOUNT_WITH_MIXED_CARDS),
        )

        assert_get_account_details_response(
            get_account_details_response_data,
            expected=expected_account_details_with_mixed_cards(
                account_id=account_with_mixed_cards_id,
                user_id=user_with_multiple_accounts_id,
            ),
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


@pytest.mark.gateway
@pytest.mark.regression
@allure.tag(AllureTag.HTTP, AllureTag.GATEWAY_SERVICE)
@allure.feature(AllureFeature.GATEWAY_SERVICE)
class TestDynamicGatewayHTTP:
    """Проверяет агрегаты Gateway на данных, зарегистрированных самим тестом."""

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. Filter registered accounts by user")
    def test_get_user_details_from_registered_scenario(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Проверяет пользователя и оба его счёта в наборе с другим владельцем.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрирует данные и возвращает контекст запроса.
        """
        user = make_user()
        other_user = make_user()
        user_accounts = [
            make_account(user_id=user.id, balance=1200.50),
            make_account(user_id=user.id, account_type=AccountTestType.CREDIT_CARD, balance=-3500.75),
        ]
        other_user_account = make_account(user_id=other_user.id)
        context = register_gateway_scenario(GatewayMockScenarioTestSchema(
            users=[other_user, user], accounts=[other_user_account, *user_accounts],
        ))
        expected = GetUserDetailsResponseTestSchema(details=UserDetailsTestSchema(user=user, accounts=user_accounts))

        get_user_details_response_data = gateway_http_test_client.get_user_details(user_id=user.id, context=context)

        assert_get_user_details_response(get_user_details_response_data, expected)

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Filter registered cards by account")
    def test_get_account_details_from_registered_scenario(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Проверяет счёт и обе его карты среди карт двух счетов одного владельца.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрирует данные и возвращает контекст запроса.
        """
        user = make_user()
        account = make_account(user_id=user.id, balance=205.25)
        other_account = make_account(user_id=user.id)
        account_cards = [
            make_card(account_id=account.id),
            make_card(account_id=account.id, card_type=CardTestType.PHYSICAL, payment_system=CardTestPaymentSystem.MASTERCARD),
        ]
        other_account_card = make_card(account_id=other_account.id)
        context = register_gateway_scenario(GatewayMockScenarioTestSchema(
            users=[user], accounts=[other_account, account], cards=[other_account_card, *account_cards],
        ))
        expected = GetAccountDetailsResponseTestSchema(
            details=AccountDetailsTestSchema(account=account, cards=account_cards),
        )

        get_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=account.id, context=context,
        )

        assert_get_account_details_response(get_account_details_response_data, expected)

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Uses the requested scenario for account and cards")
    def test_get_account_details_uses_requested_scenario(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Возвращает данные каждого сценария при одном и том же ID счёта.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрация набора и получение контекста.
        """
        first_account = make_account(user_id=uuid4(), balance=205.25)
        second_account = first_account.model_copy(update={"balance": 410.50})
        first_card = make_card(account_id=first_account.id)
        second_card = make_card(account_id=second_account.id)
        first_context = register_gateway_scenario(
            GatewayMockScenarioTestSchema(accounts=[first_account], cards=[first_card]),
        )
        second_context = register_gateway_scenario(
            GatewayMockScenarioTestSchema(accounts=[second_account], cards=[second_card]),
        )
        expected_first_details = expected_account_details(account=first_account, cards=[first_card])
        expected_second_details = expected_account_details(account=second_account, cards=[second_card])

        get_first_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=first_account.id, context=first_context,
        )
        assert_get_account_details_response(get_first_account_details_response_data, expected_first_details)

        get_second_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=first_account.id, context=second_context,
        )
        assert_get_account_details_response(get_second_account_details_response_data, expected_second_details)

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] Get account details. Account not found when cards exist")
    def test_get_account_details_returns_404_when_account_is_missing_but_cards_exist(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Возвращает ошибку Accounts при отсутствии счёта с доступными картами.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрация набора и получение контекста.
        """
        account_id = uuid4()
        card = make_card(account_id=account_id)
        context = register_gateway_scenario(GatewayMockScenarioTestSchema(cards=[card]))
        expected_detail = GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=account_id)

        mock_http_client = build_mock_admin_http_test_client()
        with mock_http_client.client:
            get_cards_response = mock_http_client.get(
                APITestRoutes.CARDS, params=QueryParams(accountId=str(account_id)), context=context,
            )
        assert_status_code(get_cards_response.status_code, HTTPStatus.OK)
        get_cards_response_data = GetCardsResponseTestSchema.model_validate_json(get_cards_response.content)
        assert_equal(get_cards_response_data.cards, [card], "cards registered for the missing account")

        get_account_details_response = gateway_http_test_client.get_account_details_api(
            account_id=account_id, context=context,
        )

        assert_gateway_not_found_response(get_account_details_response, expected_detail=expected_detail)

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. Accounts failure is isolated by scenario")
    def test_get_user_details_isolates_accounts_failure_by_scenario(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Возвращает 503 в одном сценарии и детали того же пользователя в другом.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрация набора и получение контекста.
        """
        user = make_user()
        account = make_account(user_id=user.id)
        unavailable_context = register_gateway_scenario(
            GatewayMockScenarioTestSchema(users=[user], unavailable=[GatewayMockOperation.GET_ACCOUNTS]),
        )
        healthy_context = register_gateway_scenario(
            GatewayMockScenarioTestSchema(users=[user], accounts=[account]),
        )
        expected_healthy_details = expected_user_details(user=user, accounts=[account])

        get_unavailable_user_details_response = gateway_http_test_client.get_user_details_api(
            user_id=user.id, context=unavailable_context,
        )
        assert_gateway_error_response(
            get_unavailable_user_details_response,
            expected_status=HTTPStatus.SERVICE_UNAVAILABLE,
            expected_detail=GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE,
        )

        get_healthy_user_details_response_data = gateway_http_test_client.get_user_details(
            user_id=user.id, context=healthy_context,
        )
        assert_get_user_details_response(get_healthy_user_details_response_data, expected_healthy_details)

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[HTTP] Get user details. Scenario not found after deletion")
    def test_get_user_details_returns_404_after_scenario_deletion(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Передаёт причину 404 после удаления ранее доступного сценария.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрация набора и получение контекста.
        """
        user = make_user()
        context = register_gateway_scenario(GatewayMockScenarioTestSchema(users=[user]))
        expected_details = expected_user_details(user=user, accounts=[])
        expected_detail = f"Scenario {context.scenario} not found"

        get_user_details_response_data = gateway_http_test_client.get_user_details(user_id=user.id, context=context)
        assert_get_user_details_response(get_user_details_response_data, expected_details)

        admin_client = build_mock_admin_http_test_client()
        with admin_client.client:
            admin_client.delete_scenario(context.scenario)

        get_deleted_scenario_user_details_response = gateway_http_test_client.get_user_details_api(
            user_id=user.id, context=context,
        )
        assert_gateway_not_found_response(
            get_deleted_scenario_user_details_response,
            expected_detail=expected_detail,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[HTTP] User and account details agree within one scenario")
    def test_user_and_account_details_agree_within_one_scenario(
            self,
            gateway_http_test_client: GatewayHTTPTestClient,
            register_gateway_scenario: Callable[[GatewayMockScenarioTestSchema], DynamicHTTPRequestContext],
    ) -> None:
        """Возвращает счета пользователя и детали второго счёта из одного набора.

        Args:
            gateway_http_test_client: Клиент HTTP API Gateway.
            register_gateway_scenario: Регистрация набора и получение контекста.
        """
        user = make_user()
        first_account = make_account(user_id=user.id, balance=205.25)
        second_account = make_account(user_id=user.id, balance=410.50)
        first_account_card = make_card(account_id=first_account.id)
        second_account_card = make_card(account_id=second_account.id)
        context = register_gateway_scenario(GatewayMockScenarioTestSchema(
            users=[user],
            accounts=[first_account, second_account],
            cards=[first_account_card, second_account_card],
        ))
        expected_user_details_data = expected_user_details(user=user, accounts=[first_account, second_account])
        expected_account_details_data = expected_account_details(account=second_account, cards=[second_account_card])

        get_user_details_response_data = gateway_http_test_client.get_user_details(user_id=user.id, context=context)
        assert_get_user_details_response(get_user_details_response_data, expected_user_details_data)

        get_account_details_response_data = gateway_http_test_client.get_account_details(
            account_id=second_account.id, context=context,
        )
        assert_get_account_details_response(get_account_details_response_data, expected_account_details_data)
