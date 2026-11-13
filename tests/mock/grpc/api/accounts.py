from pathlib import Path

from grpc import StatusCode
from grpc.aio import ServicerContext

from contracts.services.accounts.accounts_service_pb2_grpc import AccountsServiceServicer
from contracts.services.accounts.rpc_get_account_pb2 import GetAccountRequest, GetAccountResponse
from contracts.services.accounts.rpc_get_accounts_pb2 import GetAccountsRequest, GetAccountsResponse
from tests.context.scenario import Scenario
from tests.mock.grpc.protobuf import to_proto_account
from tests.mock.grpc.tools import resolve_grpc_scenario
from tests.mock.scenarios import DynamicScenario, ScenarioStore
from tests.schema.mock_gateway import GatewayMockOperation
from tests.tools.logger import get_test_logger
from tests.tools.mock import MockLoader
from tests.types.gateway import GatewayTestErrorReason

loader = MockLoader(
    root=Path("./tests/mock/grpc/data/accounts"),
    logger=get_test_logger("ACCOUNTS_SERVICE_MOCK_LOADER")
)


class AccountsMockService(AccountsServiceServicer):
    def __init__(self, scenario_store: ScenarioStore | None = None) -> None:
        """Принимает хранилище для динамических ответов Accounts.

        Args:
            scenario_store: Общее хранилище сценариев. При None доступны
                встроенные сценарии.
        """
        self._scenario_store = scenario_store

    async def GetAccount(self, request: GetAccountRequest, context: ServicerContext) -> GetAccountResponse:
        """Возвращает счёт сценария при совпадении запрошенного ID.

        Args:
            request: Protobuf-запрос с ID счёта.
            context: Контекст RPC с metadata x-test-scenario.

        Returns:
            Счёт выбранного сценария.

        Raises:
            grpc.aio.AbortError: С UNAVAILABLE при сбое Accounts или хранилища,
                NOT_FOUND при отсутствии сценария или счёта и INVALID_ARGUMENT
                при неверном значении x-test-scenario.
        """
        scenario = await resolve_grpc_scenario(context, self._scenario_store)
        if isinstance(scenario, DynamicScenario):
            if scenario.is_unavailable(GatewayMockOperation.GET_ACCOUNT):
                await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE.value)
            for account in scenario.available_accounts:
                if str(account.id) == request.id:
                    return GetAccountResponse(account=to_proto_account(account))
            await context.abort(
                StatusCode.NOT_FOUND,
                GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=request.id),
            )

        if scenario == Scenario.ACCOUNT_DETAILS_UNAVAILABLE:
            await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE.value)
        get_account_response_data = await loader.load_grpc(
            file=f"GetAccount/{scenario}.json",
            model=GetAccountResponse
        )
        if get_account_response_data.account.id != request.id:
            await context.abort(
                StatusCode.NOT_FOUND,
                GatewayTestErrorReason.ACCOUNT_NOT_FOUND.format(account_id=request.id),
            )
        return get_account_response_data

    async def GetAccounts(self, request: GetAccountsRequest, context: ServicerContext) -> GetAccountsResponse:
        """Возвращает счета сценария, принадлежащие запрошенному пользователю.

        Args:
            request: Protobuf-запрос с ID владельца счетов.
            context: Контекст RPC с metadata x-test-scenario.

        Returns:
            Счета с совпавшим user_id либо пустой список при отсутствии совпадений.

        Raises:
            grpc.aio.AbortError: С UNAVAILABLE при сбое Accounts или хранилища,
                NOT_FOUND при отсутствии сценария и INVALID_ARGUMENT при неверном
                значении x-test-scenario.
        """
        scenario = await resolve_grpc_scenario(context, self._scenario_store)
        if isinstance(scenario, DynamicScenario):
            if scenario.is_unavailable(GatewayMockOperation.GET_ACCOUNTS):
                await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE.value)
            return GetAccountsResponse(
                accounts=[
                    to_proto_account(account) for account in scenario.available_accounts
                    if str(account.user_id) == request.user_id
                ],
            )

        if scenario == Scenario.ACCOUNTS_LIST_UNAVAILABLE:
            await context.abort(StatusCode.UNAVAILABLE, GatewayTestErrorReason.ACCOUNTS_SERVICE_UNAVAILABLE.value)
        get_accounts_response_data = await loader.load_grpc(
            file=f"GetAccounts/{scenario}.json",
            model=GetAccountsResponse
        )
        return GetAccountsResponse(
            accounts=[
                account for account in get_accounts_response_data.accounts
                if account.user_id == request.user_id
            ]
        )
