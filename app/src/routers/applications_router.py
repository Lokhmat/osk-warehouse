from datetime import datetime
import logging
import typing

from fastapi import APIRouter, Depends, Header

from ..models import helpers
from ..models import applications
from ..models import users
from ..models.connector import db_connector
from ..utils import converters
from ..utils import crypto

applications_router = APIRouter(tags=["applications"])


@applications_router.post(
    "/applications",
    response_model=applications.Application,
    responses=helpers.BAD_REQUEST_RESPONSE,
)
async def create_application(
    x_request_idempotency_token: typing.Annotated[str, Header()],
    new_application: applications.ChangeApplicationRequest,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
):
    return applications.create_application(
        db_connector.engine,
        new_application.get_internal_application(x_request_idempotency_token, user.id),
    )


@applications_router.get(
    "/applications",
    response_model=applications.ApplicationWithActions,
    responses=helpers.NOT_FOUND_RESPONSE,
)
async def get_application(
    id: str,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
):
    application = applications.get_application_by_id(
        db_connector.engine,
        id,
    )
    if not application:
        raise helpers.NOT_FOUND_ERROR
    actions = set()
    if application.application_data.status == applications.ApplicationStatus.PENDING:
        if user.is_admin or user.is_superuser:
            actions.update(
                [
                    applications.ApplicationAction.APPROVE,
                    applications.ApplicationAction.REJECT,
                    applications.ApplicationAction.EDIT,
                ]
            )
        if user.username == application.application_data.created_by.username:
            actions.update(
                [
                    applications.ApplicationAction.EDIT,
                    applications.ApplicationAction.DELETE,
                ]
            )
    return applications.get_application_with_actions(application, list(actions))


@applications_router.patch(
    "/applications",
    response_model=applications.Application,
    responses={**helpers.BAD_REQUEST_RESPONSE, **helpers.NOT_FOUND_RESPONSE},
)
async def patch_application(
    id: str,
    new_application: applications.ChangeApplicationRequest,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
):
    return applications.update_application(
        db_connector.engine,
        new_application.get_internal_application(id, user.id),
        user.id,
    )


@applications_router.delete(
    "/applications",
    response_model=helpers.EmptyResponse,
    responses={**helpers.BAD_REQUEST_RESPONSE, **helpers.NOT_FOUND_RESPONSE},
)
async def delete_application(
    id: str,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
):
    applications.delete_application(db_connector.engine, id, user.id)
    return helpers.EmptyResponse()


@applications_router.put(
    "/applications/approve",
    response_model=helpers.EmptyResponse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def approve_application(
    id: str,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_admin_with_token)
    ],
):
    applications.approve_application(db_connector.engine, id, user.id)
    return helpers.EmptyResponse()


@applications_router.put(
    "/applications/reject",
    response_model=helpers.EmptyResponse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def reject_application(
    id: str,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_admin_with_token)
    ],
):
    applications.reject_application(db_connector.engine, id, user.id)
    return helpers.EmptyResponse()


@applications_router.get(
    "/applications/list",
    response_model=applications.ApplicationsList,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def get_applications_list(
    limit: int,
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
    status_filter: typing.Optional[applications.ApplicationStatus] = None,
    cursor: typing.Optional[datetime] = None,
):
    if user.is_superuser or user.is_admin:
        return applications.get_applications_list(
            db_connector.engine, None, cursor, limit, status_filter
        )
    return applications.get_applications_list(
        db_connector.engine, user.id, cursor, limit, status_filter
    )
