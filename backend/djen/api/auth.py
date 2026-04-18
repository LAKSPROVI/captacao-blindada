"""
Authentication module for Captacao Peticao Blindada API.

Implements JWT-based authentication with role-based access control.
"""

import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from passlib.context import CryptContext
from pydantic import BaseModel

log = logging.getLogger("captacao.auth")

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

SECRET_KEY = os.environ.get(
    "JWT_SECRET_KEY",
    "captacao-peticao-blindada-dev-secret-change-in-production",
)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# ---------------------------------------------------------------------------
# Password hashing
# ---------------------------------------------------------------------------

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# ---------------------------------------------------------------------------
# OAuth2 scheme
# ---------------------------------------------------------------------------

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenData(BaseModel):
    username: Optional[str] = None
    role: Optional[str] = None


class UserPublic(BaseModel):
    username: str
    full_name: str
    role: str


class UserInDB(BaseModel):
    username: str
    hashed_password: str
    full_name: str
    role: str  # "admin", "user", "viewer"


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "user"


# ---------------------------------------------------------------------------
# In-memory user store
# ---------------------------------------------------------------------------

_users_db: dict[str, UserInDB] = {}


def _init_default_admin() -> None:
    """Seed the store with a default admin from environment variables."""
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin")
    admin_name = os.environ.get("ADMIN_FULL_NAME", "Administrador")

    if admin_user not in _users_db:
        _users_db[admin_user] = UserInDB(
            username=admin_user,
            hashed_password=pwd_context.hash(admin_pass),
            full_name=admin_name,
            role="admin",
        )
        log.info("Default admin user '%s' created", admin_user)


_init_default_admin()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = _users_db.get(username)
    if user is None:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    return user


def create_access_token(
    data: dict,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


async def get_current_user(token: str = Depends(oauth2_scheme)) -> UserInDB:
    """Decode and validate the JWT, returning the authenticated user."""
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token invalido ou expirado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: Optional[str] = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception

    user = _users_db.get(username)
    if user is None:
        raise credentials_exception
    return user


def require_role(*allowed_roles: str):
    """Dependency factory that restricts access to specific roles.

    Usage::

        @router.get("/admin-only", dependencies=[Depends(require_role("admin"))])
        def admin_endpoint(): ...
    """

    async def _check_role(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Acesso negado. Roles permitidas: {', '.join(allowed_roles)}",
            )
        return current_user

    return _check_role


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

router = APIRouter(prefix="/api/auth", tags=["Autenticacao"])


@router.post("/login", response_model=Token, summary="Obter token de acesso")
async def login(form_data: OAuth2PasswordRequestForm = Depends()):
    """Authenticate with username/password and receive a JWT access token."""
    user = authenticate_user(form_data.username, form_data.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuario ou senha incorretos",
            headers={"WWW-Authenticate": "Bearer"},
        )

    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username, "role": user.role},
        expires_delta=expires,
    )
    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserPublic, summary="Dados do usuario autenticado")
async def me(current_user: UserInDB = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserPublic(
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
    )


@router.post("/refresh", response_model=Token, summary="Renovar token de acesso")
async def refresh_token(current_user: UserInDB = Depends(get_current_user)):
    """Issue a new access token for an already-authenticated user."""
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role},
        expires_delta=expires,
    )
    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.post(
    "/register",
    response_model=UserPublic,
    status_code=status.HTTP_201_CREATED,
    summary="Registrar novo usuario",
)
async def register(
    user_data: UserCreate,
    current_user: UserInDB = Depends(require_role("admin")),
):
    """Register a new user. Only admins can create accounts."""
    if user_data.username in _users_db:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Usuario '{user_data.username}' ja existe",
        )

    if user_data.role not in ("admin", "user", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role deve ser 'admin', 'user' ou 'viewer'",
        )

    new_user = UserInDB(
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        role=user_data.role,
    )
    _users_db[new_user.username] = new_user
    log.info("User '%s' registered by '%s'", new_user.username, current_user.username)

    return UserPublic(
        username=new_user.username,
        full_name=new_user.full_name,
        role=new_user.role,
    )
