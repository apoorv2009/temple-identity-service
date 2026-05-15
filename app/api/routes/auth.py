from fastapi import APIRouter, HTTPException

from app.schemas.auth import (
    BulkTempleAdminProvisionRequest,
    BulkTempleAdminProvisionResponse,
    ChangePasswordRequest,
    ChangePasswordResponse,
    DevoteeTempleAssignmentRequest,
    DevoteeTempleAssignmentResponse,
    ReferredDevoteeSignUpRequest,
    PushTokenDeactivateRequest,
    PushTokenLookupRequest,
    PushTokenLookupResponse,
    PushTokenRegisterRequest,
    PushTokenRegisterResponse,
    RefreshRequest,
    SignInRequest,
    SignInResponse,
    SignOutRequest,
    SignUpRequest,
    SignUpResponse,
    TempleUserLookupResponse,
    UserLookupByContactResponse,
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


@router.post("/change-password", response_model=ChangePasswordResponse)
async def change_password(payload: ChangePasswordRequest) -> ChangePasswordResponse:
    try:
        return identity_store.change_password(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/internal/referred-signup", response_model=SignUpResponse)
async def referred_signup(payload: ReferredDevoteeSignUpRequest) -> SignUpResponse:
    try:
        return identity_store.create_referred_devotee(payload)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


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


@router.post("/push-tokens/register", response_model=PushTokenRegisterResponse)
async def register_push_token(
    payload: PushTokenRegisterRequest,
) -> PushTokenRegisterResponse:
    try:
        return identity_store.register_push_token(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.post("/push-tokens/deactivate")
async def deactivate_push_token(payload: PushTokenDeactivateRequest) -> dict[str, str]:
    identity_store.deactivate_push_token(payload.user_id, payload.expo_push_token)
    return {"status": "accepted"}


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


@router.get("/internal/user-lookup/by-contact", response_model=UserLookupByContactResponse)
async def get_user_by_contact(contact_number: str) -> UserLookupByContactResponse:
    profile = identity_store.get_user_by_contact(contact_number)
    if profile is None:
        raise HTTPException(status_code=404, detail="User not found")
    return profile


@router.get("/internal/users/by-temple", response_model=TempleUserLookupResponse)
async def list_users_by_temple(
    temple_id: str,
    role: str | None = None,
) -> TempleUserLookupResponse:
    return identity_store.list_users_by_temple(temple_id=temple_id, role=role)


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


@router.post(
    "/internal/push-tokens/by-users",
    response_model=PushTokenLookupResponse,
)
async def lookup_push_tokens(
    payload: PushTokenLookupRequest,
) -> PushTokenLookupResponse:
    return identity_store.get_push_tokens_for_users(payload)


@router.post(
    "/internal/devotees/assign-temple",
    response_model=DevoteeTempleAssignmentResponse,
)
async def assign_temple_to_devotee(
    payload: DevoteeTempleAssignmentRequest,
) -> DevoteeTempleAssignmentResponse:
    try:
        return identity_store.assign_temple_to_devotee(payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
