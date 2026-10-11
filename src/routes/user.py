from fastapi import APIRouter, HTTPException, Request, status
from .schemes.user import UserCreateRequest, UserLoginRequest

from models.UserModel import UserModel


user_router = APIRouter(
    prefix="/api/v1/users",
    tags=["users"],
)


@user_router.post("")
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

    return {
        "user_uuid": str(user.user_uuid),
        "username": user.username,
        "email": user.email,
    }


@user_router.post("/login")
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

    return {
        "user_uuid": str(user.user_uuid),
        "username": user.username,
        "email": user.email,
    }