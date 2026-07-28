"""Auth routes: registration, scoped API keys."""

from datetime import datetime

from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import generate_api_key, get_current_user, hash_api_key, require_scope
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import (
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
)
from agentforge.db import get_db
from agentforge.models.api_key import APIKey
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider
from agentforge.password import PasswordTooLong, hash_password, verify_password
from agentforge.signing import generate_keypair

router = APIRouter(prefix="/v1/auth", tags=["auth"])


# --- Scoped API Key Schemas ---

class APIKeyCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=255)
    scope: str = Field(
        default="execute",
        pattern="^(read|execute|admin)$",
        description="read = list/view only, execute = submit tasks, admin = full access",
    )


class APIKeyResponse(BaseModel):
    id: str
    name: str
    scope: str
    api_key: str  # shown only once
    created_at: datetime


class APIKeyListItem(BaseModel):
    id: str
    name: str
    scope: str
    revoked: bool
    last_used_at: datetime | None
    created_at: datetime


class APIKeyListResponse(BaseModel):
    keys: list[APIKeyListItem]
    total: int


@router.post("/register", response_model=RegisterResponse)
async def register(req: RegisterRequest, db: AsyncSession = Depends(get_db)):
    """Register a new provider or consumer. Returns the API key (shown only once)."""
    model = Provider if req.role == "provider" else Consumer

    # Check for duplicate email
    existing = await db.execute(select(model).where(model.email == req.email))
    if existing.scalar_one_or_none():
        raise APIError(409, ErrorCode.ALREADY_EXISTS, "Email already registered")

    api_key = generate_api_key()
    kwargs = {"name": req.name, "email": req.email, "api_key_hash": hash_api_key(api_key)}

    if req.password:
        try:
            kwargs["password_hash"] = hash_password(req.password)
        except PasswordTooLong as exc:
            raise APIError(422, ErrorCode.INVALID_INPUT, str(exc)) from exc

    # Generate Ed25519 keypair for providers
    signing_public_key = None
    if req.role == "provider":
        pub_hex, priv_hex = generate_keypair()
        kwargs["signing_public_key"] = pub_hex
        kwargs["signing_private_key"] = priv_hex
        signing_public_key = pub_hex

    user = model(**kwargs)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    return RegisterResponse(
        id=user.id,
        name=user.name,
        email=user.email,
        role=req.role,
        api_key=api_key,
        signing_public_key=signing_public_key,
    )


@router.post("/login", response_model=LoginResponse)
async def login(req: LoginRequest, db: AsyncSession = Depends(get_db)):
    """Log in with email + password. Issues a fresh API key.

    Either a consumer or provider with this email can log in. A constant-
    time response is used whether the user exists or the password is wrong
    to reduce enumeration leakage.
    """
    # Try both tables; password_hash is the authoritative signal.
    user_obj = None
    role = None
    for role_candidate, model in (("consumer", Consumer), ("provider", Provider)):
        result = await db.execute(select(model).where(model.email == req.email))
        candidate = result.scalar_one_or_none()
        if candidate is not None and candidate.password_hash:
            if verify_password(req.password, candidate.password_hash):
                user_obj = candidate
                role = role_candidate
                break
    if user_obj is None or role is None:
        # Run one bcrypt verify to equalise timing against a found-but-wrong path.
        verify_password(req.password, "$2b$12$invalid.placeholder.to.equalise.timingXXXXXXXXXXXXXXXXXXXXXX")
        raise APIError(401, ErrorCode.INVALID_API_KEY, "Invalid email or password")

    # Issue a fresh primary API key on login.
    api_key = generate_api_key()
    user_obj.api_key_hash = hash_api_key(api_key)
    await db.commit()

    return LoginResponse(
        id=user_obj.id,
        name=user_obj.name,
        email=user_obj.email,
        role=role,
        api_key=api_key,
    )


# --- Scoped API Key Management ---


@router.post("/api-keys", response_model=APIKeyResponse)
async def create_api_key_endpoint(
    req: APIKeyCreateRequest,
    user: dict = Depends(require_scope("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Create a scoped API key. Only admin-scoped keys can create new keys.

    Scopes: read (list/view), execute (submit tasks), admin (full access).
    """
    # Limit to 10 active keys per user
    result = await db.execute(
        select(APIKey).where(
            APIKey.owner_id == user["id"],
            APIKey.revoked.is_(False),
        )
    )
    existing = result.scalars().all()
    if len(existing) >= 10:
        raise APIError(429, ErrorCode.RATE_LIMIT, "Maximum 10 active API keys")

    raw_key = generate_api_key()
    key_obj = APIKey(
        owner_id=user["id"],
        owner_role=user["role"],
        name=req.name,
        key_hash=hash_api_key(raw_key),
        scope=req.scope,
    )
    db.add(key_obj)
    await db.commit()
    await db.refresh(key_obj)

    return APIKeyResponse(
        id=str(key_obj.id),
        name=key_obj.name,
        scope=key_obj.scope,
        api_key=raw_key,
        created_at=key_obj.created_at,
    )


@router.get("/api-keys", response_model=APIKeyListResponse)
async def list_api_keys(
    user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List all API keys for the current user. Keys are masked."""
    result = await db.execute(
        select(APIKey)
        .where(APIKey.owner_id == user["id"])
        .order_by(APIKey.created_at.desc())
    )
    keys = result.scalars().all()

    return APIKeyListResponse(
        keys=[
            APIKeyListItem(
                id=str(k.id),
                name=k.name,
                scope=k.scope,
                revoked=k.revoked,
                last_used_at=k.last_used_at,
                created_at=k.created_at,
            )
            for k in keys
        ],
        total=len(keys),
    )


@router.post("/api-keys/{key_id}/revoke")
async def revoke_api_key(
    key_id: str,
    user: dict = Depends(require_scope("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Revoke an API key. Revoked keys cannot authenticate."""
    result = await db.execute(
        select(APIKey).where(APIKey.id == key_id, APIKey.owner_id == user["id"])
    )
    key_obj = result.scalar_one_or_none()
    if not key_obj:
        raise APIError(404, ErrorCode.SECRET_NOT_FOUND, "API key not found")

    key_obj.revoked = True
    await db.commit()
    return {"status": "revoked", "id": key_id}
