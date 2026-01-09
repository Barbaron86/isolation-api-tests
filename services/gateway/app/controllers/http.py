import uuid

from fastapi import HTTPException

from services.accounts.clients.http import AccountsHTTPClient, AccountsHTTPClientError
from services.cards.clients.http import CardsHTTPClient, CardsHTTPClientError
from services.gateway.app.schema.accounts import (
    AccountDetailsSchema,
    GetAccountDetailsResponseSchema
)
from services.gateway.app.schema.users import (
    UserDetailsSchema,
    GetUserDetailsResponseSchema
)
from services.users.clients.http import UsersHTTPClient, UsersHTTPClientError


async def get_user_details(
        user_id: uuid.UUID,
        users_http_client: UsersHTTPClient,
        accounts_http_client: AccountsHTTPClient
) -> GetUserDetailsResponseSchema:
    try:
        get_user_response = await users_http_client.get_user(user_id=user_id)
    except UsersHTTPClientError as error:
        raise HTTPException(
            detail=f"Get user details: {error.details}",
            status_code=error.status_code
        )

    try:
        get_accounts_response = await accounts_http_client.get_accounts(user_id=user_id)
    except AccountsHTTPClientError as error:
        raise HTTPException(
            detail=f"Get user details: {error.details}",
            status_code=error.status_code
        )

    return GetUserDetailsResponseSchema(
        details=UserDetailsSchema(
            user=get_user_response.user,
            accounts=get_accounts_response.accounts
        )
    )


async def get_account_details(
        account_id: uuid.UUID,
        cards_http_client: CardsHTTPClient,
        accounts_http_client: AccountsHTTPClient
) -> GetAccountDetailsResponseSchema:
    try:
        get_cards_response = await cards_http_client.get_cards(account_id=account_id)
    except CardsHTTPClientError as error:
        raise HTTPException(
            detail=f"Get account details: {error.details}",
            status_code=error.status_code
        )

    try:
        get_accounts_response = await accounts_http_client.get_account(account_id=account_id)
    except AccountsHTTPClientError as error:
        raise HTTPException(
            detail=f"Get account details: {error.details}",
            status_code=error.status_code
        )

    return GetAccountDetailsResponseSchema(
        details=AccountDetailsSchema(
            cards=get_cards_response.cards,
            account=get_accounts_response.account
        )
    )
