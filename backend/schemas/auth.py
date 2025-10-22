from pydantic import BaseModel, EmailStr, Field


class AuthLocalIn(BaseModel):
    """Input body for auth."""
    email: EmailStr
    password: str = Field(min_length=8)


class TokenOut(BaseModel):
    """Output body for auth."""
    access_token: str
    token_type: str = "bearer"
