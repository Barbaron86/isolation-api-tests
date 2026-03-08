import sys

import allure
import pytest

from tests.assertions.grpc.operations import (
    assert_get_operations_response_from_events,
    assert_get_operations_response_from_models,
)
from tests.clients.grpc.operations.client import OperationsGRPCTestClient
from tests.clients.kafka.operations.producer import OperationsKafkaProducerTestClient
from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.tools.allure import AllureTag, AllureStory, AllureFeature


@pytest.mark.operations
@pytest.mark.regression
@allure.feature(AllureFeature.OPERATIONS_SERVICE)
class TestOperationsGRPC:
    @allure.tag(AllureTag.GRPC, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[gRPC][Kafka] Operation events. In progress purchase operation")
    def test_operation_events_in_progress_purchase_operation(
            self,
            operations_grpc_test_client: OperationsGRPCTestClient,
            operations_kafka_producer_test_client: OperationsKafkaProducerTestClient
    ):
        # Полный event-driven флоу через gRPC API:
        # событие → асинхронный процессинг → чтение результата через gRPC.
        event = operations_kafka_producer_test_client.produce_in_progress_purchase_operation_event()
        response = operations_grpc_test_client.get_operations(user_id=event.user_id)

        assert_get_operations_response_from_events(response, [event])

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="psycopg2 + Windows Unicode limitation"
    )
    @allure.tag(AllureTag.GRPC, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[gRPC][Postgres] Filter by card id. In progress purchase operation")
    def test_filter_by_card_id_in_progress_purchase_operation(
            self,
            operations_grpc_test_client: OperationsGRPCTestClient,
            operations_postgres_test_repository: OperationsPostgresTestRepository
    ):
        # Проверка фильтрации gRPC API без участия Kafka.
        # Используется контролируемый сидинг базы данных.
        model = operations_postgres_test_repository.create_in_progress_purchase_operation()
        response = operations_grpc_test_client.get_operations(
            user_id=model.user_id,
            card_id=model.card_id
        )

        assert_get_operations_response_from_models(response, [model])
