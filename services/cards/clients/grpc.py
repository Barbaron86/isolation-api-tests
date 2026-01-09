import grpc

from config import settings
from contracts.services.cards.cards_service_pb2_grpc import CardsServiceStub
from contracts.services.cards.rpc_get_card_pb2 import GetCardRequest, GetCardResponse
from contracts.services.cards.rpc_get_cards_pb2 import GetCardsRequest, GetCardsResponse
from libs.context.base import RequestContext
from libs.context.grpc import build_grpc_metadata
from libs.grpc.client.base import GRPCClient, build_grpc_channel
from libs.logger import get_logger


class CardsGRPCClient(GRPCClient):
    def __init__(self, channel: grpc.Channel):
        super().__init__(channel)

        self.stub = CardsServiceStub(channel)

    async def get_card_api(self, request: GetCardRequest, context: RequestContext) -> GetCardResponse:
        return await self.stub.GetCard(request, metadata=build_grpc_metadata(context))

    async def get_cards_api(self, request: GetCardsRequest, context: RequestContext) -> GetCardsResponse:
        return await self.stub.GetCards(request, metadata=build_grpc_metadata(context))

    async def get_card(self, card_id: str, context: RequestContext) -> GetCardResponse:
        request = GetCardRequest(id=card_id)
        return await self.get_card_api(request, context)

    async def get_cards(self, account_id: str, context: RequestContext) -> GetCardsResponse:
        request = GetCardsRequest(account_id=account_id)
        return await self.get_cards_api(request, context)


def get_cards_grpc_client() -> CardsGRPCClient:
    channel = build_grpc_channel(
        logger=get_logger("CARDS_SERVICE_GRPC_CLIENT"),
        config=settings.cards_grpc_client
    )
    return CardsGRPCClient(channel=channel)
