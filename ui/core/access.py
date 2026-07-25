from __future__ import annotations

from typing import Any


SYSTEM_ADMIN_EMAILS = {"wangk0209@gmail.com"}


def is_system_admin(user: dict[str, Any] | None) -> bool:
    email = str((user or {}).get("email") or "").strip().lower()
    return email in SYSTEM_ADMIN_EMAILS
