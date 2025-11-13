from types import SimpleNamespace
from typing import Optional

from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken

from .models import Member


class AuthenticatedMember(SimpleNamespace):
    """
    Lightweight wrapper that behaves like a Django user for DRF permissions
    while delegating attributes to the underlying Member instance.
    """

    def __init__(self, member: Member):
        super().__init__(member=member)

    def __getattr__(self, item):
        # Delegate unknown attributes to the wrapped Member instance
        return getattr(self.member, item)

    @property
    def is_authenticated(self) -> bool:
        return True


class MemberJWTAuthentication(JWTAuthentication):
    """Custom JWT auth that resolves `user_id` to our Member model."""

    def get_user(self, validated_token) -> AuthenticatedMember:
        user_id = validated_token.get("user_id")
        if user_id is None:
            raise InvalidToken("Token contained no recognizable user identification")

        try:
            member = Member.objects.get(pk=user_id)
        except Member.DoesNotExist as exc:  # pragma: no cover
            raise InvalidToken("User not found") from exc

        return AuthenticatedMember(member)
