from sqlalchemy import select

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.database import SessionLocal
from app.models import User
from app.schemas.auth import (
    BulkTempleAdminProvisionRequest,
    BulkTempleAdminProvisionResponse,
    SignInRequest,
    SignInResponse,
    SignUpRequest,
    SignUpResponse,
    UserProfileResponse,
)

DEFAULT_ADMIN_PASSWORD = "12345678"


def _normalize_contact_number(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or value.strip()


class IdentityStore:
    def __init__(self) -> None:
        self._hasher = PasswordHasher()

    def sign_up(self, payload: SignUpRequest) -> SignUpResponse:
        normalized_contact = _normalize_contact_number(payload.contact_number)

        with SessionLocal() as session:
            existing = session.scalar(
                select(User).where(User.contact_number == normalized_contact),
            )
            if existing is not None:
                raise ValueError("User already exists with this contact number")

            user = User(
                user_id="pending",
                role="devotee",
                display_name=payload.name.strip(),
                contact_number=normalized_contact,
                password_hash=self._hasher.hash(payload.password),
                native_city=payload.native_city.strip(),
                local_area=payload.local_area.strip(),
                occupation=payload.occupation.strip(),
            )
            session.add(user)
            session.flush()
            user.user_id = self._format_user_id(user.id)
            session.commit()
            session.refresh(user)

            return SignUpResponse(user_id=user.user_id)

    def sign_in(self, payload: SignInRequest) -> SignInResponse:
        normalized_contact = _normalize_contact_number(payload.contact_number)

        with SessionLocal() as session:
            user = session.scalar(
                select(User).where(User.contact_number == normalized_contact),
            )
            if user is None:
                raise ValueError("Invalid contact number or password")

            try:
                self._hasher.verify(user.password_hash, payload.password)
            except VerifyMismatchError as exc:
                raise ValueError("Invalid contact number or password") from exc

            return SignInResponse(
                access_token=f"access-{user.user_id}",
                refresh_token=f"refresh-{user.user_id}",
                role=user.role,  # type: ignore[arg-type]
                user_id=user.user_id,
                display_name=user.display_name,
                temple_id=user.temple_id,
                temple_name=user.temple_name,
            )

    def provision_temple_admins(
        self,
        payload: BulkTempleAdminProvisionRequest,
    ) -> BulkTempleAdminProvisionResponse:
        with SessionLocal() as session:
            for admin in payload.admins:
                normalized_contact = _normalize_contact_number(admin.mobile_number)
                existing = session.scalar(
                    select(User).where(User.contact_number == normalized_contact),
                )

                if existing is not None:
                    if existing.role != "admin":
                        raise ValueError(
                            "Temple admin mobile number is already used by another app user",
                        )
                    existing.display_name = admin.name.strip()
                    existing.temple_id = payload.temple_id
                    existing.temple_name = payload.temple_name.strip()
                    existing.password_hash = self._hasher.hash(DEFAULT_ADMIN_PASSWORD)
                    continue

                user = User(
                    user_id="pending",
                    role="admin",
                    display_name=admin.name.strip(),
                    contact_number=normalized_contact,
                    password_hash=self._hasher.hash(DEFAULT_ADMIN_PASSWORD),
                    temple_id=payload.temple_id,
                    temple_name=payload.temple_name.strip(),
                )
                session.add(user)
                session.flush()
                user.user_id = self._format_user_id(user.id)

            session.commit()

        return BulkTempleAdminProvisionResponse(
            temple_id=payload.temple_id,
            admin_count=len(payload.admins),
            temporary_password_hint=DEFAULT_ADMIN_PASSWORD,
        )

    def get_profile(self, user_id: str) -> UserProfileResponse | None:
        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.user_id == user_id))
            if user is None:
                return None

            return UserProfileResponse(
                user_id=user.user_id,
                role=user.role,  # type: ignore[arg-type]
                display_name=user.display_name,
                contact_number=user.contact_number,
                native_city=user.native_city,
                local_area=user.local_area,
                occupation=user.occupation,
                temple_id=user.temple_id,
                temple_name=user.temple_name,
            )

    @staticmethod
    def _format_user_id(row_id: int) -> str:
        return f"USR-{row_id:05d}"


identity_store = IdentityStore()
