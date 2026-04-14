"""Auth routes: registration for providers and consumers."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from agentforge.api.auth import generate_api_key, hash_api_key
from agentforge.api.errors import APIError, ErrorCode
from agentforge.api.schemas import RegisterRequest, RegisterResponse
from agentforge.db import get_db
from agentforge.models.consumer import Consumer
from agentforge.models.provider import Provider
from agentforge.signing import generate_keypair

router = APIRouter(prefix="/v1/auth", tags=["auth"])


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
