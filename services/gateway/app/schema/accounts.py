from libs.schema.base import BaseSchema
from services.accounts.schema import AccountSchema
from services.cards.schema import CardSchema


class AccountDetailsSchema(BaseSchema):
    cards: list[CardSchema]
    account: AccountSchema


class GetAccountDetailsResponseSchema(BaseSchema):
    details: AccountDetailsSchema
