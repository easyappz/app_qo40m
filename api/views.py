from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Avg, Count
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiParameter

from .serializers import (
    MessageSerializer,
    MemberRegisterSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    AdListSerializer,
    AdSerializer,
    RatingInSerializer,
)
from .models import Member, Ad, Rating, Favorite
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


# -----------------------------
# Ads endpoints
# -----------------------------

class AdsPopularAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", required=False, type=int, description="Number of items to return (default 20)"),
            OpenApiParameter(name="offset", required=False, type=int, description="Offset for pagination (default 0)"),
        ],
        responses={200: {"type": "object"}},
        description=(
            "Return popular ads ranked by combined score: "
            "0.4*norm(views_count) + 0.2*norm(comments_count) + 0.15*norm(likes_count) + 0.25*norm(avg_rating)."
        ),
    )
    def get(self, request, *args, **kwargs):
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        try:
            offset = int(request.query_params.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        ads_qs = Ad.objects.all()
        ads = list(ads_qs)
        if not ads:
            return Response({"items": [], "next_offset": None}, status=status.HTTP_200_OK)

        # Collect ranges for normalization across the whole candidate set for this request
        def field_range(objs, attr):
            values = [getattr(o, attr) or 0 for o in objs]
            return (min(values), max(values))

        v_min, v_max = field_range(ads, "views_count")
        c_min, c_max = field_range(ads, "comments_count")
        l_min, l_max = field_range(ads, "likes_count")
        r_min, r_max = field_range(ads, "avg_rating")

        def norm(val, lo, hi):
            if hi == lo:
                return 0.0
            return (float(val) - float(lo)) / (float(hi) - float(lo))

        scored = []
        for ad in ads:
            score = (
                0.4 * norm(ad.views_count, v_min, v_max)
                + 0.2 * norm(ad.comments_count, c_min, c_max)
                + 0.15 * norm(ad.likes_count, l_min, l_max)
                + 0.25 * norm(ad.avg_rating, r_min, r_max)
            )
            scored.append((score, ad))

        scored.sort(key=lambda t: (t[0], t[1].created_at, t[1].id), reverse=True)

        sliced = scored[offset : offset + limit]
        items = [ad for _, ad in sliced]
        data = AdListSerializer(items, many=True).data

        next_offset = offset + limit if (offset + limit) < len(scored) else None
        return Response({"items": data, "next_offset": next_offset}, status=status.HTTP_200_OK)


class AdDetailAPIView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    @extend_schema(responses={200: AdSerializer})
    def get(self, request, ad_id: int, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=ad_id)
        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)


class RateAdAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(request=RatingInSerializer, responses={200: AdSerializer})
    def post(self, request, ad_id: int, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=ad_id)
        serializer = RatingInSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member = getattr(request.user, "member", request.user)
        value = serializer.validated_data["value"]
        if value < 1 or value > 5:
            return Response({"value": "Must be between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            Rating.objects.update_or_create(
                ad=ad,
                member=member,
                defaults={"value": value},
            )
            agg = Rating.objects.filter(ad=ad).aggregate(avg=Avg("value"), cnt=Count("id"))
            ad.avg_rating = float(agg["avg"]) if agg["avg"] is not None else 0.0
            ad.ratings_count = int(agg["cnt"]) if agg["cnt"] is not None else 0
            ad.save(update_fields=["avg_rating", "ratings_count", "updated_at"])

        return Response(AdSerializer(ad).data, status=status.HTTP_200_OK)


class ToggleFavoriteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: {"type": "object", "properties": {"is_favorite": {"type": "boolean"}}, "required": ["is_favorite"]}})
    def post(self, request, ad_id: int, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=ad_id)
        member = getattr(request.user, "member", request.user)

        fav = Favorite.objects.filter(ad=ad, member=member).first()
        if fav:
            fav.delete()
            is_favorite = False
        else:
            Favorite.objects.create(ad=ad, member=member)
            is_favorite = True
        return Response({"is_favorite": is_favorite}, status=status.HTTP_200_OK)


class MyFavoritesAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AdListSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        member = getattr(request.user, "member", request.user)
        favorites = (
            Favorite.objects.select_related("ad")
            .filter(member=member)
            .order_by("-created_at", "-id")
        )
        ads = [f.ad for f in favorites]
        return Response(AdListSerializer(ads, many=True).data, status=status.HTTP_200_OK)


class MyAdsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(responses={200: AdListSerializer(many=True)})
    def get(self, request, *args, **kwargs):
        member = getattr(request.user, "member", request.user)
        ads = Ad.objects.filter(owner=member).order_by("-created_at", "-id")
        return Response(AdListSerializer(list(ads), many=True).data, status=status.HTTP_200_OK)
