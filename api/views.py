from django.utils import timezone
from django.db.models import Q
from django.contrib.auth.hashers import check_password
from rest_framework import status, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView
from drf_spectacular.utils import extend_schema

from .serializers import (
    MessageSerializer,
    MemberRegisterSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
)
from .models import Member
from .auth import MemberJWTAuthentication


class HelloView(APIView):
    """
    A simple API endpoint that returns a greeting message.
    """

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        responses={200: MessageSerializer}, description="Get a hello world message"
    )
    def get(self, request):
        data = {"message": "Hello!", "timestamp": timezone.now()}
        serializer = MessageSerializer(data)
        return Response(serializer.data)


class RegisterAPIView(APIView):
    """POST /api/auth/register - create a new Member."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        request=MemberRegisterSerializer,
        responses={201: MemberSerializer},
        description="Register new member",
    )
    def post(self, request, *args, **kwargs):
        serializer = MemberRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member = serializer.save()
        return Response(MemberSerializer(member).data, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    """POST /api/auth/login - issue JWT for Member via username+password or email+password."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username": {"type": "string"},
                    "email": {"type": "string", "format": "email"},
                    "password": {"type": "string"},
                },
                "required": ["password"],
            }
        },
        responses={200: {"type": "object", "properties": {"access": {"type": "string"}, "refresh": {"type": "string"}}, "required": ["access", "refresh"]}},
        description="Obtain JWT tokens by username+password or email+password",
    )
    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not password or (not username and not email):
            return Response(
                {"detail": "Provide password and either username or email."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            member = Member.objects.get(Q(username=username) | Q(email__iexact=email))
        except Member.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not check_password(password, member.password):
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(member)
        # Ensure user_id claim is present (SimpleJWT already sets it as USER_ID_CLAIM)
        refresh["user_id"] = member.id

        tokens = {"refresh": str(refresh), "access": str(refresh.access_token)}
        return Response(tokens, status=status.HTTP_200_OK)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """POST /api/auth/refresh - exchange refresh for a new access token."""


class MeAPIView(APIView):
    """GET/PATCH /api/me - current member profile via JWT."""

    authentication_classes = [MemberJWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    @extend_schema(responses={200: MemberSerializer})
    def get(self, request, *args, **kwargs):
        # request.user is an AuthenticatedMember wrapper; get underlying Member
        member = getattr(request.user, "member", request.user)
        return Response(MemberSerializer(member).data, status=status.HTTP_200_OK)

    @extend_schema(request=MemberUpdateSerializer, responses={200: MemberSerializer})
    def patch(self, request, *args, **kwargs):
        member = getattr(request.user, "member", request.user)
        serializer = MemberUpdateSerializer(instance=member, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        member = serializer.save()
        return Response(MemberSerializer(member).data, status=status.HTTP_200_OK)
