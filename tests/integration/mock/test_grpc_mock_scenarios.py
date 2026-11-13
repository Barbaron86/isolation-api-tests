from asyncio import to_thread
from collections.abc import AsyncIterator
from http import HTTPStatus
from uuid import uuid4

import grpc
import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from contracts.services.accounts.account_pb2 import ACCOUNT_STATUS_ACTIVE, ACCOUNT_TYPE_DEBIT_CARD, Account
from contracts.services.accounts.accounts_service_pb2_grpc import (
    AccountsServiceStub,
    add_AccountsServiceServicer_to_server,
)
from contracts.services.accounts.rpc_get_account_pb2 import GetAccountRequest
from contracts.services.cards.card_pb2 import CARD_PAYMENT_SYSTEM_MASTERCARD, CARD_STATUS_ACTIVE, CARD_TYPE_VIRTUAL, Card
from contracts.services.cards.cards_service_pb2_grpc import CardsServiceStub, add_CardsServiceServicer_to_server
from contracts.services.cards.rpc_get_cards_pb2 import GetCardsRequest
from tests.assertions.base import assert_equal
from tests.assertions.grpc.accounts import assert_account
from tests.assertions.grpc.cards import assert_card
from tests.assertions.http.base import assert_status_code
from tests.clients.http.mock_admin import SCENARIOS_PATH
from tests.mock.grpc.api.accounts import AccountsMockService
from tests.mock.grpc.api.cards import CardsMockService
from tests.mock.http.server import create_app
from tests.schema.mock_gateway import GatewayMockScenarioTestSchema
from tests.tools.gateway_data import make_account, make_card
from tests.types.cards import CardTestPaymentSystem


@pytest.fixture
def anyio_backend() -> str:
    """Запускает интеграцию grpc.aio на asyncio."""
    return "asyncio"


@pytest.fixture
def mock_http_app() -> FastAPI:
    """Создаёт HTTP-мок с отдельным хранилищем для сценария теста."""
    return create_app(enable_dynamic_scenarios=True)


@pytest.fixture
async def mock_grpc_channel(mock_http_app: FastAPI) -> AsyncIterator[grpc.Channel]:
    """Подключает прямой gRPC-клиент к моку с общим хранилищем.

    Args:
        mock_http_app: HTTP-мок, чьё хранилище читает gRPC-мок.

    Yields:
        Канал к Accounts и Cards на локальном порту текущего теста.
    """
    scenario_store = mock_http_app.state.scenario_store
    grpc_server = grpc.aio.server()
    add_AccountsServiceServicer_to_server(AccountsMockService(scenario_store), grpc_server)
    add_CardsServiceServicer_to_server(CardsMockService(scenario_store), grpc_server)
    port = grpc_server.add_insecure_port("127.0.0.1:0")
    await grpc_server.start()
    try:
        with grpc.insecure_channel(f"127.0.0.1:{port}") as channel:
            yield channel
    finally:
        await grpc_server.stop(0)


@pytest.mark.anyio
async def test_grpc_mock_reads_admin_scenario_and_reports_its_deletion(
    mock_http_app: FastAPI, mock_grpc_channel: grpc.Channel,
) -> None:
    """Проверяет прямые RPC мока на сценарии, зарегистрированном через HTTP.

    Args:
        mock_http_app: Приложение с Admin API для регистрации и удаления.
        mock_grpc_channel: Прямой канал к gRPC-моку с тем же хранилищем.
    """
    account = make_account(user_id=uuid4(), balance=205.25)
    card = make_card(account_id=account.id, payment_system=CardTestPaymentSystem.MASTERCARD)
    other_card = make_card(account_id=uuid4())
    scenario = GatewayMockScenarioTestSchema(accounts=[account], cards=[other_card, card])
    expected_account = Account(
        id=str(account.id), user_id=str(account.user_id), balance=205.25,
        type=ACCOUNT_TYPE_DEBIT_CARD, status=ACCOUNT_STATUS_ACTIVE,
    )
    expected_card = Card(
        id=str(card.id), account_id=str(account.id), pin=card.pin, cvv=card.cvv,
        card_number=card.card_number, card_holder=card.card_holder, expiry_date=card.expiry_date.isoformat(),
        type=CARD_TYPE_VIRTUAL, status=CARD_STATUS_ACTIVE, payment_system=CARD_PAYMENT_SYSTEM_MASTERCARD,
    )

    async with AsyncClient(transport=ASGITransport(app=mock_http_app), base_url="http://testserver") as admin_client:
        create_scenario_response = await admin_client.post(
            SCENARIOS_PATH, json={"gateway": scenario.model_dump(mode="json", by_alias=True)},
        )
        assert_status_code(create_scenario_response.status_code, HTTPStatus.CREATED)
        scenario_id = create_scenario_response.json()["id"]
        metadata = (("x-test-scenario", scenario_id),)
        accounts_stub = AccountsServiceStub(mock_grpc_channel)
        cards_stub = CardsServiceStub(mock_grpc_channel)
        get_account_request = GetAccountRequest(id=str(account.id))
        get_cards_request = GetCardsRequest(account_id=str(account.id))

        get_account_response = await to_thread(
            accounts_stub.GetAccount, get_account_request, metadata=metadata, timeout=3,
        )
        assert_account(get_account_response.account, expected_account)
        get_cards_response = await to_thread(cards_stub.GetCards, get_cards_request, metadata=metadata, timeout=3)
        assert_equal(len(get_cards_response.cards), 1, "cards count")
        assert_card(get_cards_response.cards[0], expected_card)

        delete_scenario_response = await admin_client.delete(f"{SCENARIOS_PATH}/{scenario_id}")
        assert_status_code(delete_scenario_response.status_code, HTTPStatus.NO_CONTENT)

        with pytest.raises(grpc.RpcError) as get_deleted_account_error:
            await to_thread(accounts_stub.GetAccount, get_account_request, metadata=metadata, timeout=3)
        assert_equal(get_deleted_account_error.value.code(), grpc.StatusCode.NOT_FOUND, "gRPC status code")
        assert_equal(get_deleted_account_error.value.details(), f"Scenario {scenario_id} not found", "gRPC detail")
