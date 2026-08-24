from fastapi import APIRouter, Request, Response
from pydantic import BaseModel

from apps.main_api.services.session import COOKIE_NAME, SessionUser, sessions_of

router = APIRouter(prefix="/api/v1/auth")


class LoginRequest(BaseModel):
    username: str
    password: str


class SessionResponse(BaseModel):
    id: str
    role: str
    name: str
    username: str


def _body(user: SessionUser) -> SessionResponse:
    return SessionResponse(id=user.id, role=user.role, name=user.name, username=user.username)


@router.post("/login", response_model=SessionResponse)
def login(payload: LoginRequest, request: Request, response: Response):
    user = sessions_of(request).login(payload.username, payload.password)
    response.set_cookie(
        COOKIE_NAME,
        sessions_of(request).dump(user),
        httponly=True,
        samesite="lax",
        secure=False,
        path="/",
    )
    return _body(user)
