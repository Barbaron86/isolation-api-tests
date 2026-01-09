from services.operations.app.schema.operation import OperationEventSchema
from services.operations.services.postgres.repositories.operations import (
    CreateOperationDict,
    OperationsRepository,
)


def handle_operation_events(operations_repository: OperationsRepository):
    async def handle(message: str) -> None:
        event = OperationEventSchema.model_validate_json(message)
        await operations_repository.create(
            CreateOperationDict(
                type=event.type,
                status=event.status,
                amount=event.amount,
                user_id=event.user_id,
                card_id=event.card_id,
                category=event.category,
                account_id=event.account_id,
                created_at=event.created_at,
            )
        )

    return handle
