from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)
    # "Remember me" — issues a long-lived (30-day) refresh token instead of the
    # short-lived (1-day) default. Controls only the refresh token lifetime;
    # the access token TTL is unaffected.
    remember_me: bool = False
