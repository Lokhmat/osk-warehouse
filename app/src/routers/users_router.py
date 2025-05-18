import logging
import typing

from fastapi import APIRouter, Depends, Header
from fastapi.security import OAuth2PasswordRequestForm

from ..models import helpers
from ..models import users
from ..models.connector import db_connector
from ..utils import converters
from ..utils import crypto

users_router = APIRouter(tags=["users"])


@users_router.post(
    "/token", response_model=users.Token, responses=helpers.UNATHORIZED_RESPONSE
)
async def authorize(form_data: typing.Annotated[OAuth2PasswordRequestForm, Depends()]):
    user = crypto.authorize_user(
        db_connector.engine, form_data.username, form_data.password
    )
    if not user:
        logging.warning("Could not find user")
        raise helpers.UNATHORIZED_ERROR
    access_token = crypto.create_access_token(username=user.username)
    return {"access_token": access_token, "token_type": "bearer"}


@users_router.post(
    "/users",
    response_model=users.ApiUser,
    responses=helpers.BAD_REQUEST_RESPONSE,
)
async def create_user(
    new_user: users.CreateApiUser,
    x_request_idempotency_token: typing.Annotated[str, Header()],
    _: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_super_user_with_token)
    ],
):
    return converters.convert_user(
        users.create_user(
            db_connector.engine,
            x_request_idempotency_token,
            new_user,
            hash_f=crypto.hash,
        )
    )


@users_router.get(
    "/users/list",
    response_model=users.ListApiUsers,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def get_users(
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
):
    db_users = users.get_users(db_connector.engine)
    return users.ListApiUsers(items=converters.convert_users(db_users))


@users_router.get(
    "/users", response_model=users.ApiUser, responses=helpers.NOT_FOUND_RESPONSE
)
async def get_user(
    username: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
):
    user = users.get_user(db_connector.engine, username=username)
    if not user:
        raise helpers.NOT_FOUND_ERROR
    return converters.convert_user(user)


@users_router.delete(
    "/users",
    response_model=helpers.EmptyResponse,
    responses=helpers.BAD_REQUEST_RESPONSE,
)
async def delete_user(
    username: str,
    _: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_super_user_with_token)
    ],
):
    users.delete_user(db_connector.engine, username=username)
    return helpers.EmptyResponse()


@users_router.put(
    "/users", response_model=users.ApiUser, responses=helpers.NOT_FOUND_RESPONSE
)
async def update_user(
    update_user_data: users.UpdateApiUser,
    _: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_super_user_with_token)
    ],
):
    db_user = users.update_user(
        db_connector.engine, new_data=update_user_data, hash_f=crypto.hash
    )

    if not db_user:
        raise helpers.NOT_FOUND_ERROR

    return converters.convert_user(db_user)
