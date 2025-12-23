"""Data models for WhatsApp Client."""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field, field_validator, ConfigDict


class User(BaseModel):
    """User account model."""

    id: str
    username: str
    avatar: Optional[str] = None
    last_seen: int = Field(alias="lastSeen")
    token: Optional[str] = None
    role: str = "user"
    is_active: int = Field(default=1, alias="is_active")
    can_send_images: int = Field(default=1, alias="can_send_images")
    created_at: Optional[int] = Field(default=None, alias="created_at")

    model_config = ConfigDict(populate_by_name=True)


class Message(BaseModel):
    """Message model."""

    id: str
    from_user: str = Field(alias="from")
    to: str
    content: str
    timestamp: int
    status: Literal["sent", "delivered", "read"] = "sent"
    type: Literal["text", "image"] = "text"
    image_data: Optional[str] = Field(default=None, alias="imageData")

    model_config = ConfigDict(populate_by_name=True)


class RegisterRequest(BaseModel):
    """User registration request."""

    username: str
    password: str
    avatar: Optional[str] = None

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        if len(v) < 3:
            raise ValueError("Username must be at least 3 characters")
        if len(v) > 100:
            raise ValueError("Username must be at most 100 characters")
        return v

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 6:
            raise ValueError("Password must be at least 6 characters")
        return v


class LoginRequest(BaseModel):
    """User login request."""

    username: str
    password: str

    @field_validator("username", "password")
    @classmethod
    def validate_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v


class AuthResponse(BaseModel):
    """Authentication response."""

    id: str
    username: str
    avatar: Optional[str] = None
    last_seen: int = Field(alias="lastSeen")
    token: Optional[str] = None
    role: str = "user"
    is_active: int = Field(default=1, alias="is_active")
    can_send_images: int = Field(default=1, alias="can_send_images")
    created_at: Optional[int] = Field(default=None, alias="created_at")

    model_config = ConfigDict(populate_by_name=True)


class ErrorResponse(BaseModel):
    """Error response from API."""

    error: str


class PrekeyBundle(BaseModel):
    """Prekey bundle for session establishment."""

    identity_key: str
    signing_key: str
    fingerprint: str
    signed_prekey: str
    signature: str
    signed_prekey_id: Optional[int] = None
    one_time_prekeys: list = []  # Can be list[str] or list[dict] depending on context
    one_time_prekey_id: Optional[int] = None


class Session(BaseModel):
    """Encrypted session with a peer."""

    session_id: str
    peer_id: str
    shared_secret: str
    ephemeral_key: str
    initial_message_key: str
    created_at: str
    one_time_prekey_used: Optional[str] = None
    ratchet_state: Optional[dict] = None  # Serialized ratchet state
    x3dh_data: Optional[dict] = None  # X3DH data for first message (cleared after first send)
