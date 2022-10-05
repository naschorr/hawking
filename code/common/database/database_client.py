from abc import ABC, abstractmethod

from common.database.models.anonymous_item import AnonymousItem
from common.database.models.detailed_item import DetailedItem


class DatabaseClient(ABC):
    ## Properties

    @property
    @abstractmethod
    def detailed_table_name(self) -> str:
        raise NotImplementedError(f"The abstract {DatabaseClient.detailed_table_name.__name__} method hasn't been implemented yet!")


    @property
    @abstractmethod
    def anonymous_table_name(self) -> str:
        raise NotImplementedError(f"The abstract {DatabaseClient.anonymous_table_name.__name__} method hasn't been implemented yet!")


    @property
    @abstractmethod
    def detailed_table_ttl_seconds(self) -> int:
        raise NotImplementedError(f"The abstract {DatabaseClient.detailed_table_ttl_seconds.__name__} method hasn't been implemented yet!")

    ## Methods

    @abstractmethod
    async def store(self, detailed_item: DetailedItem, anonymous_item: AnonymousItem):
        raise NotImplementedError(f"The abstract {DatabaseClient.store.__name__} method hasn't been implemented yet!")


    @abstractmethod
    async def batch_delete_users(self, user_ids: list[str]):
        raise NotImplementedError(f"The abstract {DatabaseClient.batch_delete_users.__name__} method hasn't been implemented yet!")
