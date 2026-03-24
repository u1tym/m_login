from __future__ import annotations

import json
import logging
from collections.abc import Mapping, Sequence
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Any

LOG_NAME = "auth_api"
_SENSITIVE_KEYS = {
    "password",
    "passwd",
    "pass",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "cookie",
}


def setup_logging() -> logging.Logger:
    logger = logging.getLogger(LOG_NAME)
    if logger.handlers:
        return logger

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s [%(name)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    log_dir = Path("logs")
    log_dir.mkdir(exist_ok=True)
    file_handler = RotatingFileHandler(
        filename=log_dir / "auth_api.log",
        maxBytes=5 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    logger.propagate = False
    return logger


def _mask_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        masked: dict[str, Any] = {}
        for key, val in value.items():
            key_text = str(key)
            if key_text.lower() in _SENSITIVE_KEYS:
                masked[key_text] = "***"
            else:
                masked[key_text] = _mask_value(val)
        return masked
    if isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        return [_mask_value(v) for v in value]
    if isinstance(value, (bytes, bytearray)):
        return f"<{len(value)} bytes>"
    return value


def sanitize_payload(payload: Any) -> Any:
    return _mask_value(payload)


def format_payload(payload: Any) -> str:
    try:
        return json.dumps(sanitize_payload(payload), ensure_ascii=False, default=str)
    except TypeError:
        return str(sanitize_payload(payload))
