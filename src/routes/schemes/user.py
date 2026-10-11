from pydantic import BaseModel, EmailStr


class UserCreateRequest(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLoginRequest(BaseModel):
    email: EmailStr
    password: str