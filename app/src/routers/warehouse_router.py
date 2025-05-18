import typing

from fastapi import APIRouter, Depends, Header

from ..models import helpers
from ..models import users
from ..models import warehouse
from ..models.connector import db_connector
from ..utils import crypto

warehouse_router = APIRouter(tags=["warehouse"])


@warehouse_router.post(
    "/warehouse",
    response_model=warehouse.Warehouse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def create_warehouse(
    api_warehouse: warehouse.SimpleWarehouse,
    x_request_idempotency_token: typing.Annotated[str, Header()],
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    return warehouse.create_warehouse(
        engine=db_connector.engine,
        idempotency_token=x_request_idempotency_token,
        warehouse=api_warehouse,
    )


@warehouse_router.get(
    "/warehouse",
    response_model=warehouse.Warehouse,
    responses=helpers.NOT_FOUND_RESPONSE,
)
async def get_warehouse_by_id(
    warehouse_id: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
):
    db_warehouse = warehouse.get_warehouse_by_id(
        engine=db_connector.engine, id=warehouse_id
    )
    if not db_warehouse:
        raise helpers.NOT_FOUND_ERROR
    return db_warehouse


@warehouse_router.get(
    "/warehouse/list",
    response_model=warehouse.ApiWarehouseList,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def get_warehouse_list(
    user: typing.Annotated[
        users.InternalUser, Depends(crypto.authorize_user_with_token)
    ],
):
    result = warehouse.get_warehouse_list(engine=db_connector.engine)
    result = [wh for wh in result if wh.id in user.warehouses or user.is_superuser]
    return warehouse.ApiWarehouseList(items=result)


@warehouse_router.put(
    "/warehouse",
    response_model=warehouse.Warehouse,
    responses=helpers.NOT_FOUND_RESPONSE,
)
async def update_warehouse(
    warehouse_update: warehouse.WarehouseUpdate,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    db_warehouse = warehouse.update_warehouse(
        engine=db_connector.engine, warehouse_update=warehouse_update
    )
    if not db_warehouse:
        raise helpers.HTTP_404_NOT_FOUND
    return db_warehouse


@warehouse_router.delete(
    "/warehouse",
    response_model=helpers.EmptyResponse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def delete_warehouse(
    warehouse_id: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    warehouse.delete_warehouse(engine=db_connector.engine, id=warehouse_id)
    return helpers.EmptyResponse()
