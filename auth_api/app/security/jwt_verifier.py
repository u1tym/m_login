from __future__ import annotations

from typing import Any, Callable

import jwt
from fastapi import HTTPException, Request, status
from jwt.exceptions import InvalidTokenError

# 他サービス（recipe / schedule 等）でも利用できるよう、依存の少ない実装にしている。


class JWTVerifier:
    """HttpOnly Cookie に格納された JWT を検証する。他の FastAPI アプリからも利用可能。"""

    def __init__(
        self,
        *,
        secret_key: str,
        algorithm: str,
        cookie_name: str = "access_token",
    ) -> None:
        self._secret_key = secret_key
        self._algorithm = algorithm
        self._cookie_name = cookie_name

    @property
    def cookie_name(self) -> str:
        return self._cookie_name

    def get_raw_token(self, request: Request) -> str | None:
        return request.cookies.get(self._cookie_name)

    def decode_token(self, token: str) -> dict[str, Any]:
        try:
            return jwt.decode(
                token,
                self._secret_key,
                algorithms=[self._algorithm],
            )
        except InvalidTokenError as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="無効または期限切れのトークンです",
                headers={"WWW-Authenticate": "Bearer"},
            ) from e

    def verify_request(self, request: Request) -> dict[str, Any]:
        token = self.get_raw_token(request)
        if not token:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="認証が必要です",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return self.decode_token(token)

    def dependency(self) -> Callable[[Request], dict[str, Any]]:
        """FastAPI の Depends() に渡すコールバックを返す。"""

        def _dep(request: Request) -> dict[str, Any]:
            return self.verify_request(request)

        return _dep
