from datetime import datetime, timedelta, timezone
from enum import Enum
from hashlib import pbkdf2_hmac
from hmac import compare_digest
from typing import Annotated
from uuid import uuid4

import jwt
from jwt import PyJWTError
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, EmailStr

from app.config import Settings, get_settings

bearer_scheme = HTTPBearer(auto_error=False)
_PBKDF2_ITERATIONS = 120_000


class Role(str, Enum):
    ADMIN = "admin"
    AUTOMATION_ENGINEER = "automation_engineer"
    ANALYST = "analyst"
    VIEWER = "viewer"


ROLE_PERMISSIONS: dict[Role, set[str]] = {
    Role.ADMIN: {
        "process:create",
        "process:read",
        "process:execute",
        "process:approve",
        "governance:read",
        "users:manage",
    },
    Role.AUTOMATION_ENGINEER: {
        "process:create",
        "process:read",
        "process:execute",
        "governance:read",
    },
    Role.ANALYST: {"process:read", "governance:read"},
    Role.VIEWER: {"process:read"},
}


class TokenPayload(BaseModel):
    sub: EmailStr
    role: Role
    exp: int


class User(BaseModel):
    email: EmailStr
    full_name: str
    role: Role
    hashed_password: str


def hash_password(password: str, salt: str | None = None) -> str:
    used_salt = salt or uuid4().hex
    digest = pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        used_salt.encode("utf-8"),
        _PBKDF2_ITERATIONS,
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERATIONS}${used_salt}${digest}"


def verify_password(plain: str, hashed: str) -> bool:
    try:
        algorithm, iterations, salt, digest = hashed.split("$", 3)
    except ValueError:
        return False
    if algorithm != "pbkdf2_sha256":
        return False
    candidate = pbkdf2_hmac(
        "sha256",
        plain.encode("utf-8"),
        salt.encode("utf-8"),
        int(iterations),
    ).hex()
    return compare_digest(candidate, digest)


# Fixed salts keep demo hashes stable across reloads.
DEMO_USERS: dict[str, User] = {
    "engineer@example.com": User(
        email="engineer@example.com",
        full_name="Automation Engineer",
        role=Role.AUTOMATION_ENGINEER,
        hashed_password=hash_password("demo-pass-123", salt="engineer-demo-salt"),
    ),
    "admin@example.com": User(
        email="admin@example.com",
        full_name="Platform Admin",
        role=Role.ADMIN,
        hashed_password=hash_password("admin-pass-123", salt="admin-demo-salt"),
    ),
}


def create_access_token(user: User, settings: Settings) -> str:
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.access_token_expire_minutes
    )
    payload = {
        "sub": user.email,
        "role": user.role.value,
        "exp": int(expire.timestamp()),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def authenticate_user(email: str, password: str) -> User | None:
    user = DEMO_USERS.get(email)
    if not user or not verify_password(password, user.hashed_password):
        return None
    return user


def require_permission(permission: str):
    def dependency(
        credentials: Annotated[
            HTTPAuthorizationCredentials | None, Depends(bearer_scheme)
        ],
        settings: Annotated[Settings, Depends(get_settings)],
    ) -> User:
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing bearer token",
            )
        try:
            data = jwt.decode(
                credentials.credentials,
                settings.jwt_secret,
                algorithms=[settings.jwt_algorithm],
            )
            payload = TokenPayload.model_validate(data)
        except (PyJWTError, ValueError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token",
            ) from exc

        user = DEMO_USERS.get(payload.sub)
        if user is None:
            raise HTTPException(status_code=401, detail="Unknown user")
        if permission not in ROLE_PERMISSIONS[user.role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return dependency
