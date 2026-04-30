from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class LoginRequest(BaseModel):
    username: str = Field(..., min_length=1)
    password: str = Field(..., min_length=1)


class UserPublic(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str


class MeResponse(BaseModel):
    user: UserPublic


class WebPushKeys(BaseModel):
    p256dh: str = Field(..., min_length=1)
    auth: str = Field(..., min_length=1)


class WebPushSubscription(BaseModel):
    endpoint: str = Field(..., min_length=1)
    expirationTime: int | None = None
    keys: WebPushKeys


class SaveSubscriptionRequest(BaseModel):
    username: str = Field(..., min_length=1)
    subscription: WebPushSubscription


class NoticeRequest(BaseModel):
    username: str = Field(..., min_length=1)
    title: str = Field(..., min_length=1)
    message: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
