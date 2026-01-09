from pydantic import BaseModel


class RequestContext(BaseModel):
    test_scenario: str | None = None
