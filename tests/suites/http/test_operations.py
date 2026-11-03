import allure
import pytest

from tests.assertions.http.operations import (
    assert_get_operations_response_from_events,
    assert_get_operations_response_from_models,
)
from tests.clients.http.operations.client import OperationsHTTPTestClient
from tests.clients.kafka.operations.producer import OperationsKafkaProducerTestClient
from tests.clients.postgres.operations.repository import OperationsPostgresTestRepository
from tests.schema.operations import OperationEventTestSchema
from tests.tools.allure import AllureTag, AllureStory, AllureFeature
from tests.tools.fakers import fake


@pytest.mark.operations
@pytest.mark.regression
@allure.feature(AllureFeature.OPERATIONS_SERVICE)
class TestOperationsHTTP:
    """Проверяет чтение операций HTTP после прямой подготовки и Kafka-обработки."""

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. In progress purchase operation")
    def test_operation_events_in_progress_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_kafka_producer_test_client: OperationsKafkaProducerTestClient
    ) -> None:
        """Проверяет выдачу покупки IN_PROGRESS, отправленной через Kafka.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Клиент публикации событий операций.
        """
        operation_event = operations_kafka_producer_test_client.produce_in_progress_purchase_operation_event()
        get_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=operation_event.user_id,
            expected_count=1,
        )

        assert_get_operations_response_from_events(get_operations_response_data, [operation_event])

    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by card id. In progress purchase operation")
    def test_filter_by_card_id_in_progress_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_postgres_test_repository: OperationsPostgresTestRepository
    ) -> None:
        """Проверяет, что фильтр карты исключает другую покупку пользователя.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_postgres_test_repository: Подготовка операций с учётом очистки.
        """
        matching_operation_model = operations_postgres_test_repository.create_in_progress_purchase_operation()
        operations_postgres_test_repository.create_in_progress_purchase_operation(
            user_id=matching_operation_model.user_id)

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_model.user_id,
            card_id=matching_operation_model.card_id,
        )

        assert_get_operations_response_from_models(get_operations_response_data, [matching_operation_model])

    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by user id. Completed purchase operation")
    def test_filter_by_user_id_completed_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_postgres_test_repository: OperationsPostgresTestRepository,
    ) -> None:
        """Проверяет userId без карты и счёта при наличии покупки другого пользователя.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_postgres_test_repository: Подготовка операций с учётом очистки.
        """
        matching_operation_model = operations_postgres_test_repository.create_completed_purchase_operation()
        operations_postgres_test_repository.create_completed_purchase_operation()

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_model.user_id,
        )

        assert_get_operations_response_from_models(get_operations_response_data, [matching_operation_model])

    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by user id. Multiple completed purchases")
    def test_filter_by_user_id_multiple_completed_purchase_operations(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_postgres_test_repository: OperationsPostgresTestRepository,
    ) -> None:
        """Проверяет выдачу всех покупок пользователя без чужой операции.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_postgres_test_repository: Подготовка операций с учётом очистки.
        """
        first_matching_operation_model = operations_postgres_test_repository.create_completed_purchase_operation()
        second_matching_operation_model = operations_postgres_test_repository.create_completed_purchase_operation(
            user_id=first_matching_operation_model.user_id,
        )
        operations_postgres_test_repository.create_completed_purchase_operation()

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=first_matching_operation_model.user_id,
        )

        assert_get_operations_response_from_models(
            get_operations_response_data,
            [second_matching_operation_model, first_matching_operation_model],
        )

    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by user id. No operations")
    def test_filter_by_user_id_without_operations(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_postgres_test_repository: OperationsPostgresTestRepository,
    ) -> None:
        """Проверяет пустую выборку пользователя при наличии чужой покупки.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_postgres_test_repository: Подготовка операций с учётом очистки.
        """
        requested_user_id = fake.uuid()
        operations_postgres_test_repository.create_completed_purchase_operation()

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=requested_user_id,
        )

        assert_get_operations_response_from_models(get_operations_response_data, [])

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. Completed purchase operation")
    def test_operation_events_completed_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_kafka_producer_test_client: OperationsKafkaProducerTestClient
    ) -> None:
        """Проверяет выдачу покупки COMPLETED, отправленной через Kafka.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Клиент публикации событий операций.
        """
        operation_event = operations_kafka_producer_test_client.produce_completed_purchase_operation_event()
        get_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=operation_event.user_id,
            expected_count=1,
        )

        assert_get_operations_response_from_events(get_operations_response_data, [operation_event])

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. Multiple purchases for user")
    def test_operation_events_multiple_operations_for_user(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_kafka_producer_test_client: OperationsKafkaProducerTestClient,
        same_user_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
    ) -> None:
        """Проверяет сохранение обеих покупок пользователя независимо от порядка выдачи.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Публикация и учёт очистки событий.
            same_user_purchase_events: Две покупки с разными картами и полями.
        """
        first_operation_event, second_operation_event = same_user_purchase_events
        operations_kafka_producer_test_client.produce_operation_event_api(first_operation_event)
        operations_kafka_producer_test_client.produce_operation_event_api(second_operation_event)

        get_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=first_operation_event.user_id,
            expected_count=2,
        )

        assert_get_operations_response_from_events(
            get_operations_response_data,
            [second_operation_event, first_operation_event],
        )

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. Exclude another user")
    def test_operation_events_excludes_other_user(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_kafka_producer_test_client: OperationsKafkaProducerTestClient,
        different_user_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
    ) -> None:
        """Проверяет разделение пользователей после обработки обоих Kafka-событий.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Публикация и учёт очистки событий.
            different_user_purchase_events: Покупки двух независимых пользователей.
        """
        matching_operation_event, other_user_operation_event = different_user_purchase_events
        operations_kafka_producer_test_client.produce_operation_event_api(matching_operation_event)
        operations_kafka_producer_test_client.produce_operation_event_api(other_user_operation_event)

        matching_user_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=matching_operation_event.user_id,
            expected_count=1,
        )
        other_user_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=other_user_operation_event.user_id,
            expected_count=1,
        )
        assert_get_operations_response_from_events(
            matching_user_operations_response_data, [matching_operation_event],
        )
        assert_get_operations_response_from_events(
            other_user_operations_response_data, [other_user_operation_event],
        )

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_event.user_id,
        )

        assert_get_operations_response_from_events(get_operations_response_data, [matching_operation_event])

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. Filter by card")
    def test_operation_events_filters_by_card_id(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_kafka_producer_test_client: OperationsKafkaProducerTestClient,
        same_user_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
    ) -> None:
        """Проверяет фильтр карты при двух уже обработанных покупках пользователя.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Публикация и учёт очистки событий.
            same_user_purchase_events: Покупки одного счёта по разным картам.
        """
        matching_operation_event, other_card_operation_event = same_user_purchase_events
        operations_kafka_producer_test_client.produce_operation_event_api(matching_operation_event)
        operations_kafka_producer_test_client.produce_operation_event_api(other_card_operation_event)

        all_user_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=matching_operation_event.user_id,
            expected_count=2,
        )
        assert_get_operations_response_from_events(
            all_user_operations_response_data,
            [matching_operation_event, other_card_operation_event],
        )

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_event.user_id,
            card_id=matching_operation_event.card_id,
        )

        assert_get_operations_response_from_events(get_operations_response_data, [matching_operation_event])

    @allure.tag(AllureTag.HTTP, AllureTag.KAFKA, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_EVENTS)
    @allure.title("[HTTP][Kafka] Operation events. Filter by account")
    def test_operation_events_filters_by_account_id(
        self,
        operations_http_test_client: OperationsHTTPTestClient,
        operations_kafka_producer_test_client: OperationsKafkaProducerTestClient,
        different_account_purchase_events: tuple[OperationEventTestSchema, OperationEventTestSchema],
    ) -> None:
        """Проверяет фильтр счёта при двух уже обработанных покупках пользователя.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_kafka_producer_test_client: Публикация и учёт очистки событий.
            different_account_purchase_events: Покупки разных счетов одного пользователя.
        """
        matching_operation_event, other_account_operation_event = different_account_purchase_events
        operations_kafka_producer_test_client.produce_operation_event_api(matching_operation_event)
        operations_kafka_producer_test_client.produce_operation_event_api(other_account_operation_event)

        all_user_operations_response_data = operations_http_test_client.wait_for_operations(
            user_id=matching_operation_event.user_id,
            expected_count=2,
        )
        assert_get_operations_response_from_events(
            all_user_operations_response_data,
            [matching_operation_event, other_account_operation_event],
        )

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_event.user_id,
            account_id=matching_operation_event.account_id,
        )

        assert_get_operations_response_from_events(get_operations_response_data, [matching_operation_event])

    @allure.tag(AllureTag.HTTP, AllureTag.POSTGRES, AllureTag.OPERATIONS_SERVICE)
    @allure.story(AllureStory.OPERATION_FILTERS)
    @allure.title("[HTTP][Postgres] Filter by account id. Completed purchase operation")
    def test_filter_by_account_id_completed_purchase_operation(
            self,
            operations_http_test_client: OperationsHTTPTestClient,
            operations_postgres_test_repository: OperationsPostgresTestRepository
    ) -> None:
        """Проверяет, что фильтр счёта исключает другую покупку пользователя.

        Args:
            operations_http_test_client: HTTP-клиент Operations.
            operations_postgres_test_repository: Подготовка операций с учётом очистки.
        """
        matching_operation_model = operations_postgres_test_repository.create_completed_purchase_operation()
        operations_postgres_test_repository.create_completed_purchase_operation(
            user_id=matching_operation_model.user_id,
        )

        get_operations_response_data = operations_http_test_client.get_operations(
            user_id=matching_operation_model.user_id,
            account_id=matching_operation_model.account_id,
        )

        assert_get_operations_response_from_models(get_operations_response_data, [matching_operation_model])
