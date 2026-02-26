from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


# ─── Instagram Graph API Models ───────────────────────────────────────────────

class InstagramMedia(BaseModel):
    id: str
    caption: Optional[str] = None
    media_type: str
    media_url: Optional[HttpUrl] = None
    permalink: Optional[HttpUrl] = None
    thumbnail_url: Optional[HttpUrl] = None
    timestamp: datetime
    like_count: Optional[int] = None
    comments_count: Optional[int] = None


class InstagramProfile(BaseModel):
    id: str
    name: str
    biography: Optional[str] = None
    followers_count: int
    follows_count: int
    media_count: int
    profile_picture_url: Optional[HttpUrl] = None
    website: Optional[HttpUrl] = None
    username: str


class PublishMediaRequest(BaseModel):
    image_url: HttpUrl
    caption: Optional[str] = None


class PublishReelRequest(BaseModel):
    video_url: HttpUrl
    caption: Optional[str] = None
    share_to_feed: bool = True


class PaginatedMedia(BaseModel):
    data: list[InstagramMedia]
    next_cursor: Optional[str] = None


# ─── Webhook / Messenger API Models ───────────────────────────────────────────

class WebhookMessageAttachment(BaseModel):
    type: str
    payload: Optional[dict] = None


class WebhookMessage(BaseModel):
    mid: str
    text: Optional[str] = None
    attachments: Optional[list[WebhookMessageAttachment]] = None
    is_echo: Optional[bool] = None


class WebhookPostback(BaseModel):
    mid: str
    payload: str
    title: Optional[str] = None


class WebhookSender(BaseModel):
    id: str


class WebhookRecipient(BaseModel):
    id: str


class WebhookMessaging(BaseModel):
    sender: WebhookSender
    recipient: WebhookRecipient
    timestamp: int
    message: Optional[WebhookMessage] = None
    postback: Optional[WebhookPostback] = None


class WebhookEntry(BaseModel):
    id: str
    time: int
    messaging: list[WebhookMessaging]


class WebhookPayload(BaseModel):
    object: str
    entry: list[WebhookEntry]


# ─── Session Models ────────────────────────────────────────────────────────────

class UserSession(BaseModel):
    user_id: str
    state: str = "initial"
    data: dict = {}
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
