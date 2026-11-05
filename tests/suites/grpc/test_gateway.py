from uuid import UUID

import allure
import pytest
from grpc import RpcError, StatusCode

from contracts.services.gateway.rpc_get_account_details_pb2 import GetAccountDetailsRequest
from contracts.services.gateway.rpc_get_user_details_pb2 import GetUserDetailsRequest
from tests.assertions.grpc.gateway import (
    assert_gateway_rpc_error,
    assert_get_account_details_response_account_with_mixed_cards,
    assert_get_account_details_response_account_without_cards,
    assert_get_account_details_response_user_with_active_debit_card_account,
    assert_get_user_details_response_user_with_active_credit_card_account,
    assert_get_user_details_response_user_with_multiple_accounts,
    assert_get_user_details_response_user_without_accounts,
)
from tests.clients.grpc.gateway.client import GatewayGRPCTestClient
from tests.context.base import RequestContext
from tests.context.scenario import Scenario
from tests.tools.allure import AllureFeature, AllureStory, AllureTag
from tests.types.gateway import GatewayTestErrorReason


@pytest.mark.gateway
@pytest.mark.regression
@allure.tag(AllureTag.GRPC, AllureTag.GATEWAY_SERVICE)
@allure.feature(AllureFeature.GATEWAY_SERVICE)
class TestGatewayGRPC:
    """Проверяет агрегаты Gateway и передачу ошибок управляемых gRPC-зависимостей."""

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[gRPC] Get user details. User with active credit card account")
    def test_get_user_details_user_with_active_credit_card_account(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            active_credit_account_user_id: UUID,
    ) -> None:
        """Проверяет пользователя и его кредитный счёт по явно запрошенному ID.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            active_credit_account_user_id: Ожидаемый ID пользователя сценария.
        """
        get_user_details_response_data = gateway_grpc_test_client.get_user_details(
            user_id=active_credit_account_user_id,
            context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT),
        )

        assert_get_user_details_response_user_with_active_credit_card_account(
            get_user_details_response_data,
            expected_user_id=active_credit_account_user_id,
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[gRPC] Get user details. User without accounts")
    def test_get_user_details_user_without_accounts(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            user_without_accounts_id: UUID,
    ) -> None:
        """Проверяет известного пользователя с пустым списком счетов.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            user_without_accounts_id: ID существующего пользователя без счетов.
        """
        get_user_details_response_data = gateway_grpc_test_client.get_user_details(
            user_id=user_without_accounts_id,
            context=RequestContext(scenario=Scenario.USER_WITHOUT_ACCOUNTS),
        )

        assert_get_user_details_response_user_without_accounts(
            get_user_details_response_data,
            expected_user_id=user_without_accounts_id,
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[gRPC] Get user details. Multiple accounts belong to user")
    def test_get_user_details_user_with_multiple_accounts(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            user_with_multiple_accounts_id: UUID,
    ) -> None:
        """Проверяет оба счёта пользователя и отсутствие счёта другого владельца.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            user_with_multiple_accounts_id: ID владельца двух счетов в сценарии.
        """
        get_user_details_response_data = gateway_grpc_test_client.get_user_details(
            user_id=user_with_multiple_accounts_id,
            context=RequestContext(scenario=Scenario.USER_WITH_MULTIPLE_ACCOUNTS),
        )

        assert_get_user_details_response_user_with_multiple_accounts(
            get_user_details_response_data,
            expected_user_id=user_with_multiple_accounts_id,
        )

    @allure.story(AllureStory.GET_USER_DETAILS)
    @allure.title("[gRPC] Get user details. User not found")
    def test_get_user_details_user_not_found(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            unknown_user_id: UUID,
    ) -> None:
        """Проверяет NOT_FOUND и ID отсутствующего пользователя в причине ошибки.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            unknown_user_id: Корректный UUID, отсутствующий в выбранном сценарии.
        """
        get_user_details_request = GetUserDetailsRequest(id=str(unknown_user_id))
        with allure.step("Get user details and check NOT_FOUND"):
            with pytest.raises(RpcError) as get_user_details_rpc_error:
                gateway_grpc_test_client.get_user_details_api(
                    get_user_details_request,
                    context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_CREDIT_CARD_ACCOUNT),
                )

            assert_gateway_rpc_error(
                get_user_details_rpc_error.value,
                expected_code=StatusCode.NOT_FOUND,
                expected_detail=GatewayTestErrorReason.USER_NOT_FOUND.format(user_id=unknown_user_id),
            )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[gRPC] Get account details. User with active debit card account")
    def test_get_account_details_user_with_active_debit_card_account(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            active_debit_account_id: UUID,
    ) -> None:
        """Проверяет дебетовый счёт, владельца и привязанные к счёту карты.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            active_debit_account_id: Ожидаемый ID счёта сценария.
        """
        get_account_details_response_data = gateway_grpc_test_client.get_account_details(
            account_id=active_debit_account_id,
            context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT),
        )

        assert_get_account_details_response_user_with_active_debit_card_account(
            get_account_details_response_data,
            expected_account_id=active_debit_account_id,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[gRPC] Get account details. Account without cards")
    def test_get_account_details_account_without_cards(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            account_without_cards_id: UUID,
    ) -> None:
        """Проверяет существующий счёт с пустым списком карт.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            account_without_cards_id: ID существующего счёта без карт.
        """
        get_account_details_response_data = gateway_grpc_test_client.get_account_details(
            account_id=account_without_cards_id,
            context=RequestContext(scenario=Scenario.ACCOUNT_WITHOUT_CARDS),
        )

        assert_get_account_details_response_account_without_cards(
            get_account_details_response_data,
            expected_account_id=account_without_cards_id,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[gRPC] Get account details. Cards belong to account")
    def test_get_account_details_cards_belong_to_account(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            account_with_mixed_cards_id: UUID,
            user_with_multiple_accounts_id: UUID,
    ) -> None:
        """Проверяет две карты счёта и исключение карты, привязанной к другому счёту.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            account_with_mixed_cards_id: ID счёта с двумя подходящими картами.
            user_with_multiple_accounts_id: Независимый ожидаемый ID владельца счёта.
        """
        get_account_details_response_data = gateway_grpc_test_client.get_account_details(
            account_id=account_with_mixed_cards_id,
            context=RequestContext(scenario=Scenario.ACCOUNT_WITH_MIXED_CARDS),
        )

        assert_get_account_details_response_account_with_mixed_cards(
            get_account_details_response_data,
            expected_account_id=account_with_mixed_cards_id,
            expected_user_id=user_with_multiple_accounts_id,
        )

    @allure.story(AllureStory.GET_ACCOUNT_DETAILS)
    @allure.title("[gRPC] Get account details. Account not found")
    def test_get_account_details_account_not_found(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            unknown_account_id: UUID,
    ) -> None:
        """Проверяет NOT_FOUND и ID отсутствующего счёта после успешного чтения карт.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            unknown_account_id: Корректный UUID, отсутствующий в выбранном сценарии.
        """
        get_account_details_request = GetAccountDetailsRequest(id=str(unknown_account_id))
        with allure.step("Get account details and check NOT_FOUND"):
            with pytest.raises(RpcError) as get_account_details_rpc_error:
                gateway_grpc_test_client.get_account_details_api(
                    get_account_details_request,
                    context=RequestContext(scenario=Scenario.USER_WITH_ACTIVE_DEBIT_CARD_ACCOUNT),
                )

            assert_gateway_rpc_error(
                get_account_details_rpc_error.value,
                expected_code=StatusCode.NOT_FOUND,
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
    @allure.title("[gRPC] Get user details. Dependency unavailable: {scenario}")
    def test_get_user_details_dependency_unavailable(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            active_credit_account_user_id: UUID,
            scenario: Scenario,
            expected_detail: GatewayTestErrorReason,
    ) -> None:
        """Проверяет UNAVAILABLE и причину сбоя Users либо списка счетов.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            active_credit_account_user_id: ID подготовленного пользователя.
            scenario: Параметр, выбирающий сбой одной зависимости.
            expected_detail: Ожидаемая причина ошибки выбранного сервиса.
        """
        get_user_details_request = GetUserDetailsRequest(id=str(active_credit_account_user_id))
        with allure.step("Get user details and check UNAVAILABLE"):
            with pytest.raises(RpcError) as get_user_details_rpc_error:
                gateway_grpc_test_client.get_user_details_api(
                    get_user_details_request,
                    context=RequestContext(scenario=scenario),
                )

            assert_gateway_rpc_error(
                get_user_details_rpc_error.value,
                expected_code=StatusCode.UNAVAILABLE,
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
    @allure.title("[gRPC] Get account details. Dependency unavailable: {scenario}")
    def test_get_account_details_dependency_unavailable(
            self,
            gateway_grpc_test_client: GatewayGRPCTestClient,
            active_debit_account_id: UUID,
            scenario: Scenario,
            expected_detail: GatewayTestErrorReason,
    ) -> None:
        """Проверяет UNAVAILABLE и причину сбоя Cards либо получения счёта.

        Args:
            gateway_grpc_test_client: Клиент Gateway gRPC API.
            active_debit_account_id: ID подготовленного счёта.
            scenario: Параметр, выбирающий сбой одной зависимости.
            expected_detail: Ожидаемая причина ошибки выбранного сервиса.
        """
        get_account_details_request = GetAccountDetailsRequest(id=str(active_debit_account_id))
        with allure.step("Get account details and check UNAVAILABLE"):
            with pytest.raises(RpcError) as get_account_details_rpc_error:
                gateway_grpc_test_client.get_account_details_api(
                    get_account_details_request,
                    context=RequestContext(scenario=scenario),
                )

            assert_gateway_rpc_error(
                get_account_details_rpc_error.value,
                expected_code=StatusCode.UNAVAILABLE,
                expected_detail=expected_detail,
            )
