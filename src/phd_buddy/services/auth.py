"""Local-first signup and signin helpers."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


USERS_PATH = Path("vault/auth/users.json")
ITERATIONS = 210_000


@dataclass(frozen=True)
class LocalUser:
    user_id: str
    email: str
    name: str
    created_at: str
    password_salt: str
    password_hash: str

    def public_dict(self) -> dict[str, str]:
        return {
            "user_id": self.user_id,
            "email": self.email,
            "name": self.name,
            "created_at": self.created_at,
        }

    def to_dict(self) -> dict[str, str]:
        return {
            **self.public_dict(),
            "password_salt": self.password_salt,
            "password_hash": self.password_hash,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> LocalUser:
        return cls(
            user_id=str(raw["user_id"]),
            email=str(raw["email"]),
            name=str(raw.get("name", "")),
            created_at=str(raw["created_at"]),
            password_salt=str(raw["password_salt"]),
            password_hash=str(raw["password_hash"]),
        )


def signup(email: str, password: str, name: str = "", users_path: Path = USERS_PATH) -> LocalUser:
    email = _normalize_email(email)
    users = _load_users(users_path)
    if email in users:
        raise ValueError("An account with this email already exists.")

    salt = secrets.token_bytes(16)
    user = LocalUser(
        user_id=secrets.token_urlsafe(16),
        email=email,
        name=name.strip(),
        created_at=datetime.now(UTC).isoformat(),
        password_salt=_encode(salt),
        password_hash=_hash_password(password, salt),
    )
    users[email] = user
    _save_users(users, users_path)
    return user


def signin(email: str, password: str, users_path: Path = USERS_PATH) -> LocalUser:
    email = _normalize_email(email)
    user = _load_users(users_path).get(email)
    if user is None or not verify_password(password, user):
        raise ValueError("Email or password is incorrect.")
    return user


def verify_password(password: str, user: LocalUser) -> bool:
    salt = base64.b64decode(user.password_salt.encode("ascii"))
    expected = _hash_password(password, salt)
    return hmac.compare_digest(expected, user.password_hash)


def issue_session_token() -> str:
    return secrets.token_urlsafe(32)


def _load_users(path: Path) -> dict[str, LocalUser]:
    if not path.exists():
        return {}
    raw = json.loads(path.read_text(encoding="utf-8"))
    return {email: LocalUser.from_dict(payload) for email, payload in raw.items()}


def _save_users(users: dict[str, LocalUser], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps({email: user.to_dict() for email, user in users.items()}, indent=2) + "\n",
        encoding="utf-8",
    )


def _hash_password(password: str, salt: bytes) -> str:
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, ITERATIONS)
    return _encode(digest)


def _encode(value: bytes) -> str:
    return base64.b64encode(value).decode("ascii")


def _normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized:
        raise ValueError("Enter a valid email address.")
    return normalized
