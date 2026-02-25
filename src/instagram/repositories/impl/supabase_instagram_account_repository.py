from typing import List, Optional

from src.core.database.interface import IDatabaseSession
from src.core.database.supabase_async_repository import SupabaseAsyncRepository
from src.instagram.models.instagram_account import InstagramAccount
from src.instagram.repositories.instagram_account import InstagramAccountRepository


class SupabaseInstagramAccountRepository(SupabaseAsyncRepository[InstagramAccount], InstagramAccountRepository):
    def __init__(self, client: IDatabaseSession):
        super().__init__(
            client=client,
            table_name="instagram_accounts",
            model_class=InstagramAccount,
            validates_ulid=True,
            primary_key="id",
        )

    async def create_instagram_account(self, instagram_account: InstagramAccount) -> Optional[InstagramAccount]:
        data = instagram_account.model_dump(exclude_unset=True)
        return await self.create(data)

    async def get_by_id(self, account_id: str) -> Optional[InstagramAccount]:
        return await self.find_by_id(account_id)

    async def get_by_owner_id(self, owner_id: str) -> List[InstagramAccount]:
        return await self.find_by({"owner_id": owner_id})

    async def get_by_instagram_business_account_id(self, business_account_id: str) -> Optional[InstagramAccount]:
        results = await self.find_by({"instagram_business_account_id": business_account_id})
        return results[0] if results else None

    async def get_by_phone_number(self, phone_number: str) -> Optional[InstagramAccount]:
        results = await self.find_by({"phone_number": phone_number})
        return results[0] if results else None

    async def update_instagram_account(self, account_id: str, data: dict) -> Optional[InstagramAccount]:
        return await self.update(account_id, data)

    async def delete_instagram_account(self, account_id: str) -> bool:
        return await self.delete(account_id)
