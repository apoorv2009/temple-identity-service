from datetime import UTC, datetime

from sqlalchemy import select

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

from app.core.database import SessionLocal
from app.models import User, UserPushToken
from app.schemas.auth import (
    BulkTempleAdminProvisionRequest,
    BulkTempleAdminProvisionResponse,
    PushTokenItem,
    PushTokenLookupRequest,
    PushTokenLookupResponse,
    PushTokenRegisterRequest,
    PushTokenRegisterResponse,
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

    def register_push_token(
        self,
        payload: PushTokenRegisterRequest,
    ) -> PushTokenRegisterResponse:
        with SessionLocal() as session:
            user = session.scalar(select(User).where(User.user_id == payload.user_id))
            if user is None:
                raise ValueError("User not found")

            now = datetime.now(UTC)
            existing = session.scalar(
                select(UserPushToken).where(
                    UserPushToken.expo_push_token == payload.expo_push_token,
                ),
            )

            if existing is not None:
                existing.user_id = payload.user_id
                existing.platform = payload.platform
                existing.device_label = payload.device_label.strip() if payload.device_label else None
                existing.is_active = True
                existing.last_seen_at = now
                session.commit()
                session.refresh(existing)
                return self._to_push_token_response(existing)

            record = UserPushToken(
                token_id="pending",
                user_id=payload.user_id,
                expo_push_token=payload.expo_push_token,
                platform=payload.platform,
                device_label=payload.device_label.strip() if payload.device_label else None,
                is_active=True,
                last_seen_at=now,
            )
            session.add(record)
            session.flush()
            record.token_id = self._format_push_token_id(record.id)
            session.commit()
            session.refresh(record)
            return self._to_push_token_response(record)

    def deactivate_push_token(self, user_id: str, expo_push_token: str) -> None:
        with SessionLocal() as session:
            record = session.scalar(
                select(UserPushToken).where(
                    UserPushToken.user_id == user_id,
                    UserPushToken.expo_push_token == expo_push_token,
                ),
            )
            if record is None:
                return

            record.is_active = False
            record.updated_at = datetime.now(UTC)
            session.commit()

    def get_push_tokens_for_users(
        self,
        payload: PushTokenLookupRequest,
    ) -> PushTokenLookupResponse:
        with SessionLocal() as session:
            items = session.scalars(
                select(UserPushToken)
                .where(
                    UserPushToken.user_id.in_(payload.user_ids),
                    UserPushToken.is_active.is_(True),
                )
                .order_by(UserPushToken.updated_at.desc()),
            ).all()

            return PushTokenLookupResponse(
                items=[
                    PushTokenItem(
                        token_id=item.token_id,
                        user_id=item.user_id,
                        expo_push_token=item.expo_push_token,
                        platform=item.platform,  # type: ignore[arg-type]
                        device_label=item.device_label,
                        is_active=item.is_active,
                    )
                    for item in items
                ],
            )

    @staticmethod
    def _format_user_id(row_id: int) -> str:
        return f"USR-{row_id:05d}"

    @staticmethod
    def _format_push_token_id(row_id: int) -> str:
        return f"TOK-{row_id:05d}"

    @staticmethod
    def _to_push_token_response(record: UserPushToken) -> PushTokenRegisterResponse:
        return PushTokenRegisterResponse(
            token_id=record.token_id,
            user_id=record.user_id,
            expo_push_token=record.expo_push_token,
            platform=record.platform,  # type: ignore[arg-type]
            is_active=record.is_active,
        )


identity_store = IdentityStore()
