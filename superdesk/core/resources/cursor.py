# -*- coding: utf-8; -*-
#
# This file is part of Superdesk.
#
# Copyright 2024 Sourcefabric z.u. and contributors.
#
# For the full copyright and license information, please see the
# AUTHORS and LICENSE files distributed with this source code, or
# at https://www.sourcefabric.org/superdesk/license

from typing import Any, Generic, TypeVar, Type

from motor.motor_asyncio import AsyncIOMotorCollection, AsyncIOMotorCursor

from .model import ResourceModel


ResourceModelType = TypeVar("ResourceModelType", bound=ResourceModel)


class ResourceCursorAsync(Generic[ResourceModelType]):
    def __init__(self, data_class: Type[ResourceModelType]):
        self.data_class = data_class

    def __aiter__(self):
        return self

    async def __anext__(self) -> ResourceModelType:
        raise NotImplementedError()

    async def next(self) -> ResourceModelType | None:
        raise NotImplementedError()

    async def next_raw(self) -> dict[str, Any] | None:
        raise NotImplementedError()

    async def to_list(self) -> list[ResourceModelType]:
        items: list[ResourceModelType] = []
        item = await self.next_raw()
        while item is not None:
            items.append(self.get_model_instance(item))
            item = await self.next_raw()
        return items

    async def to_list_raw(self) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        item = await self.next_raw()
        while item is not None:
            item["_type"] = self.data_class.model_resource_name
            items.append(item)
            item = await self.next_raw()
        return items

    async def count(self):
        raise NotImplementedError()

    def get_model_instance(self, data: dict[str, Any]):
        """Get a model instance from a dictionary of values

        :param data: Dictionary containing values to get a model instance from
        :rtype: ResourceModelType
        :return: A model instance
        """

        # We can't use ``model_construct`` method to construct instance without validation
        # because nested models are not being converted to model instances
        data.pop("_type", None)
        return self.data_class.from_dict(data)


class ElasticsearchResourceCursorAsync(ResourceCursorAsync[ResourceModelType], Generic[ResourceModelType]):
    _index: int
    hits: dict[str, Any]
    no_hits = {"hits": {"total": 0, "hits": []}}

    def __init__(self, data_class: Type[ResourceModelType], hits=None):
        """Parse hits into docs."""

        super().__init__(data_class)
        self._index = 0
        self.hits = hits if hits else self.no_hits

    async def __anext__(self) -> ResourceModelType:
        item = await self.next()
        if item is not None:
            return item
        raise StopAsyncIteration

    async def next(self) -> ResourceModelType | None:
        item_dict = await self.next_raw()
        return None if item_dict is None else self.get_model_instance(item_dict)

    async def next_raw(self) -> dict[str, Any] | None:
        try:
            data = self.hits["hits"]["hits"][self._index]
            source = data["_source"]
            source["_id"] = data["_id"]
            source["_type"] = source.pop("_resource", None)
            self._index += 1
            return source
        except (IndexError, KeyError, TypeError):
            self._index = 0
            return None

    async def count(self):
        hits = self.hits.get("hits")
        if hits:
            total = hits.get("total")
            if isinstance(total, int):
                return total
            elif isinstance(total, dict) and total.get("value"):
                return int(total["value"])
        return 0

    def extra(self, response: dict[str, Any]):
        """Add extra info to response"""
        if "facets" in self.hits:
            response["_facets"] = self.hits["facets"]
        if "aggregations" in self.hits:
            response["_aggregations"] = self.hits["aggregations"]


class MongoResourceCursorAsync(ResourceCursorAsync[ResourceModelType], Generic[ResourceModelType]):
    def __init__(
        self,
        data_class: Type[ResourceModelType],
        collection: AsyncIOMotorCollection,
        cursor: AsyncIOMotorCursor,
        lookup: dict[str, Any],
    ):
        super().__init__(data_class)
        self.collection = collection
        self.cursor = cursor
        self.lookup = lookup

    async def __anext__(self) -> ResourceModelType:
        item = await self.next()
        if item is not None:
            return item
        raise StopAsyncIteration

    async def next(self) -> ResourceModelType | None:
        try:
            return self.get_model_instance(dict(await self.cursor.next()))
        except StopAsyncIteration:
            self.cursor.rewind()
            return None

    async def next_raw(self) -> dict[str, Any] | None:
        try:
            return dict(await self.cursor.next())
        except StopAsyncIteration:
            self.cursor.rewind()
            return None

    async def count(self):
        return await self.collection.count_documents(self.lookup)