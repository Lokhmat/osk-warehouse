from datetime import datetime, timedelta
import logging
import os
import typing

from jose import jwt, JWTError
from passlib.context import CryptContext

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from ..constants import JWT_ALGORITHM, JWT_EXPIRE_MINUTES
from ..models import users
from ..models.connector import db_connector
from ..models.helpers import NO_PERMISSIONS_ERROR, UNATHORIZED_ERROR

pwd_context = CryptContext(schemes=["sha256_crypt"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


def hash(data: str):
    return pwd_context.hash(data)


def create_access_token(username: str):
    to_encode = {"sub": username}
    expires_at = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    to_encode.update({"exp": expires_at})
    encoded_jwt = jwt.encode(
        to_encode, key=os.environ.get("JWT_SECRET_KEY"), algorithm=JWT_ALGORITHM
    )
    return encoded_jwt


def verify_password(password: str, password_hash: str):
    return pwd_context.verify(password, password_hash)


def authorize_user(
    connection, username: str, password: str
) -> typing.Optional[users.SimpleUser]:
    user = users.get_simple_user(connection, username)
    if not user:
        logging.info("Could not fing user in DB")
        return False
    if not verify_password(password, user.password_hash):
        logging.info("Failed to verify user's password")
        return False
    return user


def authorize_user_with_token(
    token: typing.Annotated[str, Depends(oauth2_scheme)],
) -> users.InternalUser:
    try:
        payload = jwt.decode(
            token, os.environ.get("JWT_SECRET_KEY"), algorithms=[JWT_ALGORITHM]
        )
        username: str = payload.get("sub")
        if username is None:
            raise UNATHORIZED_ERROR
    except JWTError:
        raise UNATHORIZED_ERROR
    user = users.get_user(db_connector.engine, username=username)
    if user is None:
        raise UNATHORIZED_ERROR
    return user


def authorize_super_user_with_token(
    token: typing.Annotated[str, Depends(oauth2_scheme)],
) -> users.InternalUser:
    user = authorize_user_with_token(token=token)
    if not user.is_superuser:
        raise NO_PERMISSIONS_ERROR
    return user


def authorize_admin_with_token(
    token: typing.Annotated[str, Depends(oauth2_scheme)],
) -> users.InternalUser:
    user = authorize_user_with_token(token=token)
    if not user.is_admin and not user.is_superuser:
        raise NO_PERMISSIONS_ERROR
    return user
