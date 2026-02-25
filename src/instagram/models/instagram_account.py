import uuid

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class InstagramAccount(BaseModel):
    """
    Model representing an Instagram account linked to a user.
    """
    id: str = Field(default_factory=uuid.uuid7, description="Unique identifier for the account")
    owner_id: str = Field(description="ID of the user who owns the account - ULID")
    instagram_business_account_id: str = Field(description="Instagram business account ID")
    phone_number: str = Field(default=None, description="Phone number associated with the account")
    access_token: str = Field(description="Access token for Instagram API")
    refresh_token: str = Field(description="Refresh token for Instagram API")
    expires_at: datetime = Field(default=None, default_factory=datetime.now, description="Expiration time of the access token")
    created_at: datetime = Field(default=None, default_factory=datetime.now, description="Account creation time")
    updated_at: datetime = Field(default=None, default_factory=datetime.now, description="Account last update time")

    model_config = ConfigDict(from_attributes=True)

    def __repr__(self) -> str:
        return f"InstagramAccount(id={self.id}, owner_id={self.owner_id}, instagram_business_account_id={self.instagram_business_account_id}, phone_number={self.phone_number})"