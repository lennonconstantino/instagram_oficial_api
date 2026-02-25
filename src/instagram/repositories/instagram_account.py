from abc import ABC, abstractmethod
from typing import List, Optional

from src.instagram.models.instagram_account import InstagramAccount


class InstagramAccountRepository(ABC):
    @abstractmethod
    async def create_instagram_account(self, instagram_account: InstagramAccount) -> Optional[InstagramAccount]:
        ...

    @abstractmethod
    async def get_by_id(self, account_id: str) -> Optional[InstagramAccount]:
        ...


    @abstractmethod
    async def get_by_owner_id(self, owner_id: str) -> List[InstagramAccount]:
        ...

    @abstractmethod
    async def get_by_instagram_business_account_id(self, business_account_id: str) -> Optional[InstagramAccount]:
        ...

    @abstractmethod
    async def get_by_phone_number(self, phone_number: str) -> Optional[InstagramAccount]:
        ...

    @abstractmethod
    async def update_instagram_account(self, account_id: str, data: dict) -> Optional[InstagramAccount]:
        ...

    @abstractmethod
    async def delete_instagram_account(self, account_id: str) -> bool:
        ...
