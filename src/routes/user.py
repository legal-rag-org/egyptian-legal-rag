from fastapi import APIRouter, HTTPException, Request, status, Depends
from .schemes.user import UserCreateRequest, UserLoginRequest, UserResponse, LoginResponse

from models.UserModel import UserModel
from models.db_schemes.insurance_rag.schemes import User

from typing import Annotated

from utils.auth import get_current_user, create_access_token



user_router = APIRouter(
    prefix="/api/v1/users",
    tags=["api_v1","users"],
)


@user_router.post("", response_model=UserResponse)
async def create_user(
    request: Request,
    user_data: UserCreateRequest,
):
    user_model = await UserModel.create_instance(
        db_client=request.app.db_client
    )

    existing_user = await user_model.get_user_by_email(
        email=user_data.email
    )

    if existing_user is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists.",
        )

    user = await user_model.create_user(
        username=user_data.username,
        email=user_data.email,
        password=user_data.password,
    )

    return UserResponse(
        user_uuid=user.user_uuid,
        username=user.username,
        email=user.email,
    )


@user_router.post("/login", response_model=LoginResponse)
async def login_user(
    request: Request,
    user_data: UserLoginRequest,
):
    user_model = await UserModel.create_instance(
        db_client=request.app.db_client
    )

    user = await user_model.get_user_by_email(
        email=user_data.email
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    password_valid = await user_model.verify_password(
        password=user_data.password,
        password_hash=user.password_hash,
    )

    if not password_valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    access_token = create_access_token(
        user_uuid=str(user.user_uuid)
    )

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": {
            "user_uuid": str(user.user_uuid),
            "username": user.username,
            "email": user.email,
        },
    }



@user_router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: Annotated[
        User,
        Depends(get_current_user),
    ],
):
    return current_user
