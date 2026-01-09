import uuid
from typing import Annotated

from fastapi import APIRouter, Depends

from libs.routes import APIRoutes
from services.accounts.clients.http import AccountsHTTPClient, get_accounts_http_client
from services.cards.clients.http import get_cards_http_client, CardsHTTPClient
from services.gateway.app.controllers.http import get_user_details, get_account_details
from services.gateway.app.schema.accounts import GetAccountDetailsResponseSchema
from services.gateway.app.schema.users import GetUserDetailsResponseSchema
from services.users.clients.http import get_users_http_client, UsersHTTPClient

gateway_router = APIRouter(
    prefix=APIRoutes.GATEWAY,
    tags=[APIRoutes.GATEWAY.as_tag()]
)


@gateway_router.get(
    '/user-details/{user_id}',
    response_model=GetUserDetailsResponseSchema
)
async def get_user_details_view(
        user_id: uuid.UUID,
        users_http_client: Annotated[UsersHTTPClient, Depends(get_users_http_client)],
        accounts_http_client: Annotated[AccountsHTTPClient, Depends(get_accounts_http_client)],
):
    return await get_user_details(
        user_id=user_id,
        users_http_client=users_http_client,
        accounts_http_client=accounts_http_client
    )


@gateway_router.get(
    '/account-details/{account_id}',
    response_model=GetAccountDetailsResponseSchema
)
async def get_account_details_view(
        account_id: uuid.UUID,
        cards_http_client: Annotated[CardsHTTPClient, Depends(get_cards_http_client)],
        accounts_http_client: Annotated[AccountsHTTPClient, Depends(get_accounts_http_client)],
):
    return await get_account_details(
        account_id=account_id,
        cards_http_client=cards_http_client,
        accounts_http_client=accounts_http_client
    )
