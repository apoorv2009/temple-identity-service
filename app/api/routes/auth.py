from fastapi import APIRouter

from app.schemas.auth import RefreshRequest, SignInRequest, SignInResponse, SignOutRequest

router = APIRouter()


@router.post("/signin", response_model=SignInResponse)
async def signin(payload: SignInRequest) -> SignInResponse:
    return SignInResponse(
        access_token=f"stub-access-token-for-{payload.contact_number}",
        refresh_token=f"stub-refresh-token-for-{payload.contact_number}",
        role="devotee",
    )


@router.post("/refresh")
async def refresh(payload: RefreshRequest) -> dict[str, str]:
    return {
        "access_token": f"rotated-{payload.refresh_token}",
        "token_type": "bearer",
        "phase": "scaffold",
    }


@router.post("/signout")
async def signout(payload: SignOutRequest) -> dict[str, str]:
    return {"status": "accepted", "refresh_token": payload.refresh_token}


@router.get("/me")
async def me() -> dict[str, object]:
    return {
        "id": "devotee-001",
        "name": "Scaffold User",
        "role": "devotee",
        "contact_number_masked": "98XXXXXX10",
        "phase": "scaffold",
    }

