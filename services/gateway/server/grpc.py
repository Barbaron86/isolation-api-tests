import asyncio

from grpc_reflection.v1alpha import reflection

from config import settings
from contracts.services.gateway import gateway_service_pb2, gateway_service_pb2_grpc
from libs.grpc.server.base import build_grpc_server
from libs.logger import get_logger
from services.gateway.app.api.grpc import GatewayService


async def serve():
    logger = get_logger("GATEWAY_SERVICE_GRPC_SERVER")
    server = build_grpc_server(settings.gateway_grpc_server, logger)

    gateway_service_pb2_grpc.add_GatewayServiceServicer_to_server(GatewayService(), server)

    reflection.enable_server_reflection(
        (
            reflection.SERVICE_NAME,
            gateway_service_pb2.DESCRIPTOR.services_by_name['GatewayService'].full_name,
        ),
        server
    )

    await server.start()
    await server.wait_for_termination()


if __name__ == '__main__':
    asyncio.run(serve())
