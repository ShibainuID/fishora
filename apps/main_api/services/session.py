"""Signed session cookies for the two seeded demo roles."""

from __future__ import annotations

import hashlib
import hmac
import json
from base64 import urlsafe_b64decode, urlsafe_b64encode
from dataclasses import dataclass

from fastapi import Request

from apps.main_api.errors import Forbidden, Unauthenticated

COOKIE_NAME = "fishora_session"
DEFAULT_SESSION_SECRET = "fishora-dev-session"

DEMO_USERS = {
    "rian": {
        "id": "op_rian",
        "role": "operator",
        "password": "demo",
        "name": "Rian Setiawan",
    },
    "dewi": {
        "id": "buyer_dewi",
        "role": "buyer",
        "password": "demo",
        "name": "Dewi Anggraini",
    },
}


@dataclass(frozen=True)
class SessionUser:
    id: str
    role: str
    name: str
    username: str


class SessionService:
    def __init__(self, secret: str = DEFAULT_SESSION_SECRET):
        self._secret = secret.encode("utf-8")

    def login(self, username: str, password: str) -> SessionUser:
        record = DEMO_USERS.get(username)
        if record is None or record["password"] != password:
            raise Unauthenticated()
        return SessionUser(
            id=record["id"], role=record["role"], name=record["name"], username=username
        )

    def dump(self, user: SessionUser) -> str:
        payload = urlsafe_b64encode(json.dumps({
            "id": user.id, "role": user.role, "name": user.name, "username": user.username,
        }).encode("utf-8"))
        signature = hmac.new(self._secret, payload, hashlib.sha256).hexdigest()
        return f"{payload.decode('ascii')}.{signature}"

    def load(self, token: str | None) -> SessionUser | None:
        if not token or "." not in token:
            return None
        payload, signature = token.rsplit(".", 1)
        expected = hmac.new(self._secret, payload.encode("ascii"), hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected, signature):
            return None
        try:
            data = json.loads(urlsafe_b64decode(payload.encode("ascii")))
            return SessionUser(
                id=data["id"], role=data["role"], name=data["name"], username=data["username"]
            )
        except (KeyError, ValueError, json.JSONDecodeError):
            return None


def sessions_of(request: Request) -> SessionService:
    return request.app.state.deps.session_service or SessionService()


def current_user(request: Request) -> SessionUser:
    user = sessions_of(request).load(request.cookies.get(COOKIE_NAME))
    if user is None:
        raise Unauthenticated()
    return user


def require_role(request: Request, role: str) -> SessionUser:
    user = current_user(request)
    if user.role != role:
        raise Forbidden(f"{role} role required")
    return user
