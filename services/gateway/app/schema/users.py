from libs.schema.base import BaseSchema
from services.accounts.schema import AccountSchema
from services.users.schema import UserSchema


class UserDetailsSchema(BaseSchema):
    user: UserSchema
    accounts: list[AccountSchema]


class GetUserDetailsResponseSchema(BaseSchema):
    details: UserDetailsSchema
