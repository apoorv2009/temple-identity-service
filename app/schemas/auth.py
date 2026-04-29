from pydantic import BaseModel, Field


class SignInRequest(BaseModel):
    contact_number: str = Field(..., min_length=10, max_length=20)
    password: str = Field(..., min_length=8, max_length=128)


class SignInResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    role: str
    phase: str = "scaffold"


class RefreshRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)


class SignOutRequest(BaseModel):
    refresh_token: str = Field(..., min_length=10)

