from hmac import new
import logging
import typing

from pydantic import BaseModel

from sqlalchemy import text

from ..constants import BASE_POSTGRES_TRANSACTIONS_DIRECTORY
from ..models import helpers


class Item(BaseModel):
    id: str
    item_name: str
    item_type: typing.Optional[str]
    manufacturer: typing.Optional[str]
    model: typing.Optional[str]
    description: typing.Optional[str]
    codes: typing.List[str]


class CreateItem(BaseModel):
    item_name: str
    item_type: typing.Optional[str] = None
    manufacturer: typing.Optional[str] = None
    model: typing.Optional[str] = None
    description: typing.Optional[str] = None
    codes: typing.List[str]

    def get_item(self, idempotency_token: str) -> Item:
        return Item(
            id=idempotency_token,
            item_name=self.item_name,
            item_type=self.item_type,
            manufacturer=self.manufacturer,
            model=self.model,
            description=self.description,
            codes=self.codes,
        )


class UpdateItem(BaseModel):
    id: str
    item_name: typing.Optional[str] = None
    item_type: typing.Optional[str] = None
    manufacturer: typing.Optional[str] = None
    model: typing.Optional[str] = None
    description: typing.Optional[str] = None
    codes: typing.Optional[typing.List[str]] = None


class ItemWithCount(Item):
    count: int


class ItemWithWarehouseCount(Item):
    warehouse_count: typing.Mapping[str, int] = (
        dict()
    )  # warehouse name to item count on warehouse


class ListItems(BaseModel):
    items: typing.List[Item]


class ListItemsWithCount(BaseModel):
    items: typing.List[ItemWithCount]


class ItemCategory(BaseModel):
    category_name: str


class ItemCategoriesList(BaseModel):
    categories: typing.List[ItemCategory]


def create_item(engine, idempotency_token: str, new_item: CreateItem):
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/check_new_item_codes.sql"
        ) as sql:
            query = text(sql.read())
            args = {"codes": new_item.codes, "id": None}
            existing_items = connection.execute(query, args).all()
            if existing_items:
                raise helpers.get_bad_request(
                    f"Товары с такими ШК уже существуют: {' '.join([e.item_name for e in existing_items])}"
                )
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/create_item.sql"
        ) as sql:
            query = text(sql.read())
            args = new_item.get_item(idempotency_token).model_dump()
            for row in connection.execute(query, args):
                result = Item(**row._mapping)
        connection.commit()
    logging.info("Created item card")
    return result


def get_item_by_id(engine, item_id: str):
    item: typing.Optional[ItemWithWarehouseCount] = None
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/get_item_by_id.sql"
        ) as sql:
            query = text(sql.read())
            for row in connection.execute(query, {"item_id": item_id}):
                item = ItemWithWarehouseCount(**row._mapping)
        if item:
            with open(
                f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/get_item_count_by_id.sql"
            ) as sql:
                query = text(sql.read())
                for row in connection.execute(query, {"item_id": item_id}):
                    item.warehouse_count[row.warehouse_name] = row.item_count
        connection.commit()
    return item


def get_items_list(
    engine,
    item_name: typing.Optional[str],
    item_cat: typing.Optional[str],
):
    items: typing.List[Item] = []
    with engine.connect() as connection:
        with open(f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/get_items.sql") as sql:
            query = text(sql.read())
            for row in connection.execute(
                query,
                {
                    "item_name": item_name,
                    "item_cat": item_cat,
                },
            ):
                items.append(Item(**row._mapping))
        connection.commit()
    return ListItems(items=items)


def get_items_by_warehouse(
    engine,
    warehouse_id: str,
    item_name: typing.Optional[str],
    item_cat: typing.Optional[str],
):
    items: typing.List[ItemWithCount] = []
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/get_item_count_by_warehouse.sql"
        ) as sql:
            query = text(sql.read())
            for row in connection.execute(
                query,
                {
                    "warehouse_id": warehouse_id,
                    "item_name": item_name,
                    "item_cat": item_cat,
                },
            ):
                items.append(ItemWithCount(**row._mapping))
        connection.commit()
    return ListItemsWithCount(items=items)


def update_item(engine, new_item_data: UpdateItem):
    result: typing.Optional[Item] = None
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/check_new_item_codes.sql"
        ) as sql:
            query = text(sql.read())
            args = {"codes": new_item_data.codes, "id": new_item_data.id}
            existing_items = connection.execute(query, args).all()
            if existing_items:
                raise helpers.get_bad_request(
                    f"Товары с такими ШК уже существуют: {' '.join([e.item_name for e in existing_items])}"
                )
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/update_item.sql"
        ) as sql:
            query = text(sql.read())
            args = new_item_data.model_dump()
            for row in connection.execute(query, args):
                result = Item(**row._mapping)
        connection.commit()
    return result


def delete_item(engine, item_id: str):
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/delete_item.sql"
        ) as sql:
            query = text(sql.read())
            connection.execute(query, {"item_id": item_id})
        connection.commit()


def create_item_category(engine, category: ItemCategory):
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/create_category.sql"
        ) as sql:
            query = text(sql.read())
            connection.execute(query, {"category_name": category.category_name})
        connection.commit()


def get_item_categories(engine) -> ItemCategoriesList:
    with engine.connect() as connection:
        with open(
            f"{BASE_POSTGRES_TRANSACTIONS_DIRECTORY}/items/get_categories.sql"
        ) as sql:
            query = text(sql.read())
            categories = connection.execute(query).all()
        connection.commit()
    return ItemCategoriesList(
        categories=[
            ItemCategory(category_name=category.category_name)
            for category in categories
        ]
    )
