from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import Settings, get_settings
from ..database import get_db
from ..models import Account
from ..schemas import LoginRequest, MeResponse, UserPublic
from ..security.jwt_tokens import create_access_token
from ..security.jwt_verifier import JWTVerifier
from ..security.password import verify_password

router = APIRouter(tags=["auth"])


def _get_verifier(settings: Settings = Depends(get_settings)) -> JWTVerifier:
    return JWTVerifier(
        secret_key=settings.secret_key,
        algorithm=settings.algorithm,
        cookie_name=settings.cookie_name,
    )


@router.post("/login", status_code=status.HTTP_200_OK)
def login(
    body: LoginRequest,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    account = db.execute(
        select(Account).where(
            Account.username == body.username,
            Account.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if account is None or not verify_password(body.password, account.password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザー名またはパスワードが正しくありません",
        )

    now = datetime.utcnow()
    account.last_access = now
    account.updated_at = now
    db.add(account)
    db.commit()

    token = create_access_token(
        subject=str(account.id),
        extra_claims={"username": account.username},
        settings=settings,
    )
    max_age = settings.access_token_expire_minutes * 60
    response.set_cookie(
        key=settings.cookie_name,
        value=token,
        max_age=max_age,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"message": "ok"}


@router.post("/logout", status_code=status.HTTP_200_OK)
def logout(
    response: Response,
    settings: Settings = Depends(get_settings),
) -> dict[str, str]:
    response.delete_cookie(
        key=settings.cookie_name,
        path="/",
        httponly=True,
        secure=True,
        samesite="lax",
    )
    return {"message": "ok"}


@router.get("/me", response_model=MeResponse)
def me(
    request: Request,
    db: Session = Depends(get_db),
    verifier: JWTVerifier = Depends(_get_verifier),
) -> MeResponse:
    claims = verifier.verify_request(request)
    sub = claims.get("sub")
    if sub is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="トークンに subject がありません",
        )
    try:
        user_id = int(sub)
    except (TypeError, ValueError) as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="無効な subject です",
        ) from e

    account = db.execute(
        select(Account).where(
            Account.id == user_id,
            Account.is_deleted.is_(False),
        )
    ).scalar_one_or_none()
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ユーザーが見つかりません",
        )
    return MeResponse(user=UserPublic.model_validate(account))
