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
from fastlite import Database

from djen.api.audit import registrar_auditoria

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
    tenant_id: Optional[int] = None


class UserPublic(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    tenant_id: Optional[int] = None


class UserInDB(BaseModel):
    id: int
    username: str
    hashed_password: str
    full_name: str
    role: str  # "master", "tenant_admin", "manager", "operator", "viewer"
    tenant_id: Optional[int] = None


class UserCreate(BaseModel):
    username: str
    password: str
    full_name: str
    role: str = "viewer"
    tenant_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Database Helpers
# ---------------------------------------------------------------------------
def _get_db():
    from djen.api.app import get_database
    return get_database()

def _init_default_admin() -> None:
    """Seed the DB with a default Master admin if no users exist."""
    admin_user = os.environ.get("ADMIN_USERNAME", "admin")
    admin_pass = os.environ.get("ADMIN_PASSWORD", "admin")
    admin_name = os.environ.get("ADMIN_FULL_NAME", "Administrador Master")

    try:
        db = _get_db()
        cur = db.conn.execute("SELECT id FROM users LIMIT 1")
        if not cur.fetchone():
            hashed_pw = hash_password(admin_pass)
            db.conn.execute(
                "INSERT INTO users (tenant_id, username, hashed_password, full_name, role) VALUES (?, ?, ?, ?, ?)",
                (1, admin_user, hashed_pw, admin_name, 'master')
            )
            db.conn.commit()
            log.info("Default master user '%s' created", admin_user)
    except BaseException as e:
        log.error("Could not init default admin: %s", e)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def get_user_from_db(username: str) -> Optional[UserInDB]:
    db = _get_db()
    row = db.conn.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
    if row:
        return UserInDB(**dict(row))
    return None


def authenticate_user(username: str, password: str) -> Optional[UserInDB]:
    user = get_user_from_db(username)
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

    user = get_user_from_db(username)
    if user is None:
        raise credentials_exception
    return user


def require_role(*allowed_roles: str):
    """Dependency factory that restricts access to specific roles."""

    async def _check_role(current_user: UserInDB = Depends(get_current_user)) -> UserInDB:
        if current_user.role not in allowed_roles and "master" not in allowed_roles: # master sempre pode tudo? dependendo da logica.
            if current_user.role != "master":
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail=f"Acesso negado. Roles permitidas: {', '.join(allowed_roles)}",
                )
        return current_user

    return _check_role

def require_master_or_tenant_admin():
    return require_role("master", "tenant_admin")

# Inicializa o default admin
_init_default_admin()


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
        data={"sub": user.username, "role": user.role, "tenant_id": user.tenant_id},
        expires_delta=expires,
    )
    
    registrar_auditoria("LOG_IN", "auth", str(user.id), {"username": user.username, "tenant": user.tenant_id}, user.id, user.tenant_id)
    
    return Token(
        access_token=access_token,
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserPublic, summary="Dados do usuario autenticado")
async def me(current_user: UserInDB = Depends(get_current_user)):
    """Return the profile of the currently authenticated user."""
    return UserPublic(
        id=current_user.id,
        username=current_user.username,
        full_name=current_user.full_name,
        role=current_user.role,
        tenant_id=current_user.tenant_id,
    )


@router.post("/refresh", response_model=Token, summary="Renovar token de acesso")
async def refresh_token(current_user: UserInDB = Depends(get_current_user)):
    """Issue a new access token for an already-authenticated user."""
    expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username, "role": current_user.role, "tenant_id": current_user.tenant_id},
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
    current_user: UserInDB = Depends(require_master_or_tenant_admin()),
):
    """Register a new user. Only master or tenant_admins can create accounts."""
    db = _get_db()
    existing = get_user_from_db(user_data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Usuario '{user_data.username}' ja existe",
        )

    if user_data.role not in ("master", "tenant_admin", "manager", "operator", "viewer"):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Role invalida.",
        )

    # Regras: tenant_admin nao pode criar "master" nem "tenant_admin" para outro tenant.
    target_tenant_id = user_data.tenant_id
    if current_user.role != "master":
        if user_data.role in ("master", "tenant_admin"):
            raise HTTPException(status_code=403, detail="Apenas master pode criar master/tenant_admin.")
        target_tenant_id = current_user.tenant_id

    hashed_pw = hash_password(user_data.password)
    cur = db.conn.execute(
        "INSERT INTO users (tenant_id, username, hashed_password, full_name, role) VALUES (?, ?, ?, ?, ?)",
        (target_tenant_id, user_data.username, hashed_pw, user_data.full_name, user_data.role)
    )
    db.conn.commit()
    new_user_id = cur.lastrowid
    log.info("User '%s' registered by '%s'", user_data.username, current_user.username)

    registrar_auditoria("USER_CREATED", "users", str(new_user_id), 
                        {"username": user_data.username, "role": user_data.role, "created_by": current_user.username}, 
                        current_user.id, target_tenant_id)

    return UserPublic(
        id=new_user_id,
        username=user_data.username,
        full_name=user_data.full_name,
        role=user_data.role,
        tenant_id=target_tenant_id,
    )

