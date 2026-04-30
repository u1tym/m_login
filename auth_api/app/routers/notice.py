from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException, status
from pywebpush import WebPushException, webpush
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import Account, NoticeSubscription
from ..schemas import NoticeRequest, SaveSubscriptionRequest

router = APIRouter(tags=["notice"])


@router.post("/save-subscription", status_code=status.HTTP_200_OK)
def save_subscription(
    body: SaveSubscriptionRequest,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    account = db.execute(
        select(Account).where(
            Account.username == body.username,
            Account.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    subscription_text = body.subscription.model_dump_json()
    record = db.get(NoticeSubscription, account.id)
    if record is None:
        db.add(NoticeSubscription(aid=account.id, subscription=subscription_text))
    else:
        record.subscription = subscription_text
        db.add(record)
    db.commit()
    return {"message": "ok"}


@router.post("/notice", status_code=status.HTTP_200_OK)
def send_notice(
    body: NoticeRequest,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    if not settings.vapid_private_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="VAPID_PRIVATE_KEY が設定されていません",
        )

    account = db.execute(
        select(Account).where(
            Account.username == body.username,
            Account.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ユーザーが見つかりません",
        )

    record = db.get(NoticeSubscription, account.id)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="subscription が登録されていません",
        )

    try:
        subscription_info = json.loads(record.subscription)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="subscription の形式が不正です",
        ) from exc

    payload = json.dumps(
        {"title": body.title, "message": body.message, "url": body.url},
        ensure_ascii=False,
    )

    try:
        webpush(
            subscription_info=subscription_info,
            data=payload,
            vapid_private_key=settings.vapid_private_key,
            vapid_claims={"sub": settings.vapid_claims_sub},
        )
    except WebPushException as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"webpush 送信に失敗しました: {exc}",
        ) from exc

    return {"message": "ok"}
