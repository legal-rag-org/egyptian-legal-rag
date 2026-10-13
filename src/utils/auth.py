from fastapi import HTTPException, status, Depends, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from datetime import datetime, timedelta, timezone

import jwt

from helpers.config import get_settings
from .enums.auth import AuthEnums

from typing import Annotated


from models.UserModel import UserModel


bearer_scheme = HTTPBearer()



def create_access_token(user_uuid: str) -> str:
    settings = get_settings()

    now = datetime.now(timezone.utc)

    payload = {
        "sub": str(user_uuid),
        "iat": now,
        "exp": now + timedelta(
            minutes=settings.JWT_ACCESS_TOKEN_EXPIRE_MINUTES
        ),
    }

    return jwt.encode(
        payload,
        settings.JWT_SECRET_KEY,
        algorithm=settings.JWT_ALGORITHM,
    )



def decode_access_token(token: str) -> str:
    settings = get_settings()

    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
        )

        user_uuid = payload.get("sub")

        if not user_uuid:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=AuthEnums.INVALID_ACESS_TOKEN.value,
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user_uuid

    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthEnums.INVALID_OR_EXPIRED_ACESS_TOKEN.value,
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    request: Request,
    credentials: Annotated[
        HTTPAuthorizationCredentials,
        Depends(bearer_scheme),
    ],
):
    user_uuid = decode_access_token(credentials.credentials)

    user_model = await UserModel.create_instance(
        db_client=request.app.db_client
    )

    user = await user_model.get_user_by_uuid(
        user_uuid=user_uuid
    )

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=AuthEnums.USER_NOT_FOUND.value,
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user

