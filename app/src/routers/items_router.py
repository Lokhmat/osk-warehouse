import logging
import typing

from fastapi import APIRouter, Depends, Header

from ..models import helpers
from ..models import items
from ..models import users
from ..models.connector import db_connector
from ..utils import crypto

items_router = APIRouter(tags=["items"])


@items_router.post(
    "/items", response_model=items.Item, responses=helpers.BAD_REQUEST_RESPONSE
)
async def create_item(
    new_item: items.CreateItem,
    x_request_idempotency_token: typing.Annotated[str, Header()],
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    return items.create_item(db_connector.engine, x_request_idempotency_token, new_item)


@items_router.get(
    "/items",
    response_model=items.ItemWithWarehouseCount,
    responses=helpers.NOT_FOUND_RESPONSE,
)
async def get_item(
    item_id: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
):
    item = items.get_item_by_id(db_connector.engine, item_id)
    if not item:
        return helpers.NOT_FOUND_ERROR
    return item


@items_router.put(
    "/items",
    response_model=items.Item,
    responses=helpers.NOT_FOUND_RESPONSE,
)
async def update_item(
    new_item_data: items.UpdateItem,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    item = items.update_item(db_connector.engine, new_item_data)
    if not item:
        return helpers.NOT_FOUND_ERROR
    return item


@items_router.delete(
    "/items",
    response_model=helpers.EmptyResponse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def delete_item(
    item_id: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    items.delete_item(db_connector.engine, item_id)
    return helpers.EmptyResponse()


@items_router.get(
    "/items/list",
    response_model=items.ListItems,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def get_items_list(
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
    item_name: typing.Optional[str] = None,
    item_cat: typing.Optional[str] = None,
):
    return items.get_items_list(db_connector.engine, item_name, item_cat)


@items_router.get(
    "/items/by-warehouse",
    response_model=items.ListItemsWithCount,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def get_items_list_by_warehouse(
    warehouse_id: str,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
    item_name: typing.Optional[str] = None,
    item_cat: typing.Optional[str] = None,
):
    return items.get_items_by_warehouse(
        db_connector.engine, warehouse_id, item_name, item_cat
    )


@items_router.post(
    "/item/category",
    response_model=helpers.EmptyResponse,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def create_item_category(
    category: items.ItemCategory,
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_admin_with_token)],
):
    items.create_item_category(db_connector.engine, category)
    return helpers.EmptyResponse()


@items_router.get(
    "/item/category/list",
    response_model=items.ItemCategoriesList,
    responses=helpers.UNATHORIZED_RESPONSE,
)
async def create_item_category(
    _: typing.Annotated[users.InternalUser, Depends(crypto.authorize_user_with_token)],
):
    return items.get_item_categories(db_connector.engine)
