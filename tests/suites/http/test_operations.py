import sys

import allure
import pytest

from tests.assertions.http.operations import (
    assert_get_operations_response_from_events,
    assert_get_operations_response_from_models,
)
from tests.clients.http.operations.client import OperationsHTTPTestClient
from tests.clients.kafka.operations.producer import OperationsKafkaProducerTestClient
from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.tools.allure import AllureTag, AllureStory, AllureFeature


@pytest.mark.operations
@pytest.mark.regression
@allure.feature(AllureFeature.OPERATIONS_SERVICE)
class TestOperationsHTTP:
    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. In progress purchase operation")
    def test_operation_events_in_progress_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_kafka_producer_test_client: OperationsKafkaProducerTestClient
    ):
        # В этом тесте мы проверяем полный event-driven флоу:
        # 1. Публикуем событие операции в Kafka.
        # 2. Ожидаем, что процессор асинхронно обработает событие.
        # 3. Проверяем результат через синхронный HTTP API.
        #
        # Такой тест валидирует интеграцию Kafka, процессинга,
        # сохранения состояния и HTTP-контракта operations-service.
        event = operations_kafka_producer_test_client.produce_in_progress_purchase_operation_event()
        response = operations_http_test_client.get_operations(user_id=event.user_id)

        assert_get_operations_response_from_events(response, [event])

    @pytest.mark.skipif(
        sys.platform == "win32",
        reason="psycopg2 + Windows Unicode limitation"
    )
    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by card id. In progress purchase operation")
    def test_filter_by_card_id_in_progress_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_postgres_test_repository: OperationsPostgresTestRepository
    ):
        # В этом тесте нас не интересует асинхронный флоу.
        # Мы проверяем только корректность фильтрации HTTP API.
        #
        # Поэтому мы напрямую сидим контролируемое состояние в базу данных,
        # что делает тест:
        # - быстрее;
        # - стабильнее;
        # - проще для чтения и поддержки.
        model = operations_postgres_test_repository.create_in_progress_purchase_operation()
        response = operations_http_test_client.get_operations(
            user_id=model.user_id,
            card_id=model.card_id
        )

        assert_get_operations_response_from_models(response, [model])
