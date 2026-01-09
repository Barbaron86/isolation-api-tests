from fastapi import FastAPI

from config import settings
from libs.http.server.base import build_http_server
from services.gateway.app.api.http import gateway_router

app = FastAPI(title="gateway-service")

app.include_router(gateway_router)

if __name__ == "__main__":
    build_http_server("services.gateway.server.http:app", settings.gateway_http_server)
