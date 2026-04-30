from fastapi import APIRouter, HTTPException

from app.schemas.auth import (
    BulkTempleAdminProvisionRequest,
    BulkTempleAdminProvisionResponse,
    RefreshRequest,
    SignInRequest,
    SignInResponse,
    SignOutRequest,
    SignUpRequest,
    SignUpResponse,
    UserProfileResponse,
)
from app.services.identity import DEFAULT_ADMIN_PASSWORD, identity_store

router = APIRouter()


@router.post("/signup", response_model=SignUpResponse)
async def signup(payload: SignUpRequest) -> SignUpResponse:
    try:
        return identity_store.sign_up(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.post("/signin", response_model=SignInResponse)
async def signin(payload: SignInRequest) -> SignInResponse:
    try:
        return identity_store.sign_in(payload)
    except ValueError as exc:
        raise HTTPException(status_code=401, detail=str(exc)) from exc


@router.post("/refresh")
async def refresh(payload: RefreshRequest) -> dict[str, str]:
    return {
        "access_token": f"rotated-{payload.refresh_token}",
        "token_type": "bearer",
        "phase": "app_access",
    }


@router.post("/signout")
async def signout(payload: SignOutRequest) -> dict[str, str]:
    return {"status": "accepted", "refresh_token": payload.refresh_token}


@router.get("/me")
async def me() -> dict[str, object]:
    return {
        "bootstrap_admin_password_hint": DEFAULT_ADMIN_PASSWORD,
        "phase": "app_access",
    }


@router.get("/internal/users/{user_id}", response_model=UserProfileResponse)
async def get_user_profile(user_id: str) -> UserProfileResponse:
    profile = identity_store.get_profile(user_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.post(
    "/internal/temple-admins/bulk",
    response_model=BulkTempleAdminProvisionResponse,
)
async def provision_temple_admins(
    payload: BulkTempleAdminProvisionRequest,
) -> BulkTempleAdminProvisionResponse:
    try:
        return identity_store.provision_temple_admins(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc
