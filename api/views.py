from django.utils import timezone
from django.db import transaction
from django.db.models import Q, Avg, Count, Max
from django.shortcuts import get_object_or_404
from django.contrib.auth.hashers import check_password
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView as SimpleJWTTokenRefreshView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from rest_framework.viewsets import ViewSet

from .serializers import (
    MessageSerializer,
    MemberRegisterSerializer,
    MemberSerializer,
    MemberUpdateSerializer,
    AdListSerializer,
    AdSerializer,
    RatingInSerializer,
    CommentSerializer,
    CommentCreateSerializer,
    ImportRequestSerializer,
    ImportJobSerializer,
)
from .models import Member, Ad, Rating, Favorite, Comment, CommentLike, AdView, ImportJob
from .auth import MemberJWTAuthentication
from .services import record_unique_view, fetch_avito_metadata, import_listing_from_url, LocalRateLimitError


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
    """POST /api/auth/login - issue JWT for Member via username_or_email + password."""

    authentication_classes: list = []
    permission_classes: list = []

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {
                    "username_or_email": {"type": "string"},
                    "password": {"type": "string"},
                },
                "required": ["username_or_email", "password"],
            }
        },
        responses={
            200: {
                "type": "object",
                "properties": {"access": {"type": "string"}, "refresh": {"type": "string"}},
                "required": ["access", "refresh"],
            }
        },
        description="Obtain JWT tokens by username_or_email and password",
    )
    def post(self, request, *args, **kwargs):
        # Primary (per OpenAPI)
        identifier = request.data.get("username_or_email")
        password = request.data.get("password")

        # Backward-compatible fallbacks
        if not identifier:
            identifier = request.data.get("username") or request.data.get("email")
        if not password or not identifier:
            return Response(
                {"detail": "Provide 'username_or_email' and 'password'."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            member = Member.objects.get(Q(username=identifier) | Q(email__iexact=identifier))
        except Member.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        if not check_password(password, member.password):
            return Response({"detail": "Invalid credentials."}, status=status.HTTP_401_UNAUTHORIZED)

        refresh = RefreshToken.for_user(member)
        refresh["user_id"] = member.id
        tokens = {"refresh": str(refresh), "access": str(refresh.access_token)}
        return Response(tokens, status=status.HTTP_200_OK)


class TokenRefreshView(SimpleJWTTokenRefreshView):
    """POST /api/auth/refresh - exchange refresh for a new access token and return both tokens."""

    def post(self, request, *args, **kwargs):
        resp = super().post(request, *args, **kwargs)
        try:
            data = dict(resp.data) if isinstance(resp.data, dict) else {}
        except Exception:
            data = {}
        # Ensure both tokens are present per OpenAPI spec
        if "refresh" not in data:
            refresh_in = request.data.get("refresh")
            if isinstance(refresh_in, str) and refresh_in:
                data["refresh"] = refresh_in
        resp.data = data
        return resp


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


class AdImportAPIView(APIView):
    """POST /api/ads/import - create Ad from an Avito URL.

    Notes: Only publicly available metadata is fetched. If blocked by site protections, no circumvention is performed.
    """

    authentication_classes = [MemberJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        request={
            "application/json": {
                "type": "object",
                "properties": {"url": {"type": "string", "format": "uri"}},
                "required": ["url"],
            }
        },
        responses={
            201: AdSerializer,
            400: {"type": "object"},
            422: {"type": "object"},
        },
        description=(
            "Import ad metadata from a public Avito URL and create an Ad. "
            "Only public data is fetched; if blocked by protections, no bypass is attempted."
        ),
    )
    def post(self, request, *args, **kwargs):
        url = (request.data or {}).get("url")
        if not url or not isinstance(url, str):
            return Response({"detail": "Field 'url' is required."}, status=status.HTTP_400_BAD_REQUEST)

        result = fetch_avito_metadata(url)
        if not result.get("ok"):
            code = result.get("code") or "parse_failed"
            detail = result.get("detail") or "Failed to fetch metadata."
            return Response(
                {
                    "code": code,
                    "detail": detail,
                    "message": "Could not fetch public metadata. Please enter fields manually.",
                    "note": "No circumvention of site protections is performed.",
                },
                status=422,
            )

        data = result["data"]
        member = None
        if getattr(request, "user", None) and getattr(request.user, "is_authenticated", False):
            member = getattr(request.user, "member", request.user)

        ad = Ad.objects.create(
            owner=member,
            source_url=url,
            title=(data.get("title") or ""),
            description=(data.get("description") or ""),
            price=int(data.get("price") or 0),
            photos=list(data.get("photos") or []),
        )
        return Response(AdSerializer(ad).data, status=status.HTTP_201_CREATED)


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


# -----------------------------
# Views counter endpoint (unique per 24h)
# -----------------------------

class AdViewCreateAPIView(APIView):
    """POST /api/ads/{id}/views - record unique view; returns updated views_count."""

    authentication_classes = [MemberJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id", required=True, type=int, location=OpenApiParameter.PATH),
        ],
        responses={200: {"type": "object", "properties": {"views_count": {"type": "integer"}}, "required": ["views_count"]}},
        description=(
            "Record a unique view (24h window). Authenticated users are unique by (ad, member). "
            "Guests are approximated by fingerprint sha256(ip + '|' + user_agent)."
        ),
    )
    def post(self, request, ad_id: int, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=ad_id)
        views_count = record_unique_view(request, ad)
        return Response({"views_count": views_count}, status=status.HTTP_200_OK)


# -----------------------------
# Comments endpoints
# -----------------------------

class AdCommentsListCreateAPIView(APIView):
    """GET list comments of ad (paginated, by created_at). POST create comment (JWT)."""

    authentication_classes = [MemberJWTAuthentication]
    permission_classes = [AllowAny]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="id", required=True, type=int, location=OpenApiParameter.PATH),
            OpenApiParameter(name="limit", required=False, type=int, description="Number of items to return (default 20)"),
            OpenApiParameter(name="offset", required=False, type=int, description="Offset for pagination (default 0)"),
            OpenApiParameter(name="parent", required=False, type=int, description="If provided, returns replies for this comment id. If omitted, returns top-level comments."),
        ],
        responses={200: {"type": "object"}},
        description="List comments for ad by created_at. If parent is set, returns replies only.",
    )
    def get(self, request, ad_id: int, *args, **kwargs):
        ad = get_object_or_404(Ad, pk=ad_id)
        try:
            limit = int(request.query_params.get("limit", 20))
        except (TypeError, ValueError):
            limit = 20
        try:
            offset = int(request.query_params.get("offset", 0))
        except (TypeError, ValueError):
            offset = 0
        parent = request.query_params.get("parent")
        parent_id = None
        if parent is not None:
            try:
                parent_id = int(parent)
            except (TypeError, ValueError):
                return Response({"parent": "Must be an integer."}, status=status.HTTP_400_BAD_REQUEST)

        limit = max(1, min(limit, 100))
        offset = max(0, offset)

        qs = Comment.objects.select_related("author").filter(ad=ad)
        if parent_id is None:
            qs = qs.filter(parent__isnull=True)
        else:
            qs = qs.filter(parent_id=parent_id)

        qs = qs.order_by("created_at", "id")
        total = qs.count()
        items = list(qs[offset : offset + limit])
        data = CommentSerializer(items, many=True).data
        next_offset = offset + limit if (offset + limit) < total else None
        return Response({"items": data, "next_offset": next_offset}, status=status.HTTP_200_OK)

    @extend_schema(
        request=CommentCreateSerializer,
        responses={201: CommentSerializer, 400: {"type": "object"}, 401: {"type": "object"}},
        description="Create a new comment for the ad. Optional parent for reply.",
    )
    def post(self, request, ad_id: int, *args, **kwargs):
        if not request.user or not getattr(request.user, "is_authenticated", False):
            return Response({"detail": "Authentication credentials were not provided."}, status=status.HTTP_401_UNAUTHORIZED)

        ad = get_object_or_404(Ad, pk=ad_id)
        serializer = CommentCreateSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        member = getattr(request.user, "member", request.user)
        parent_id = serializer.validated_data.get("parent")
        parent = None
        if parent_id is not None:
            parent = get_object_or_404(Comment, pk=parent_id)
            if parent.ad_id != ad.id:
                return Response({"parent": "Parent comment belongs to a different ad."}, status=status.HTTP_400_BAD_REQUEST)

        comment = Comment.objects.create(
            ad=ad,
            author=member,
            parent=parent,
            text=serializer.validated_data["text"],
        )
        return Response(CommentSerializer(comment).data, status=status.HTTP_201_CREATED)


class CommentDeleteAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter(name="id", required=True, type=int, location=OpenApiParameter.PATH)],
        responses={204: None, 403: {"type": "object"}, 404: {"type": "object"}},
        description="Delete a comment. Only the author can delete.",
    )
    def delete(self, request, comment_id: int, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=comment_id)
        member = getattr(request.user, "member", request.user)
        if comment.author_id != member.id:
            return Response({"detail": "You do not have permission to delete this comment."}, status=status.HTTP_403_FORBIDDEN)
        comment.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class ToggleCommentLikeAPIView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[OpenApiParameter(name="id", required=True, type=int, location=OpenApiParameter.PATH)],
        responses={200: {"type": "object", "properties": {"is_liked": {"type": "boolean"}, "likes_count": {"type": "integer"}}, "required": ["is_liked", "likes_count"]}, 404: {"type": "object"}},
        description="Toggle like on a comment. Updates comment and ad like counters.",
    )
    def post(self, request, comment_id: int, *args, **kwargs):
        comment = get_object_or_404(Comment, pk=comment_id)
        member = getattr(request.user, "member", request.user)

        like = CommentLike.objects.filter(comment=comment, member=member).first()
        if like:
            like.delete()
            is_liked = False
        else:
            CommentLike.objects.create(comment=comment, member=member)
            is_liked = True

        comment.refresh_from_db(fields=["likes_count"])
        return Response({"is_liked": is_liked, "likes_count": comment.likes_count}, status=status.HTTP_200_OK)


# -----------------------------
# Me -> History (recent unique ads by last view time)
# -----------------------------

class MyHistoryAPIView(APIView):
    authentication_classes = [MemberJWTAuthentication]
    permission_classes = [IsAuthenticated]

    @extend_schema(
        parameters=[
            OpenApiParameter(name="limit", required=False, type=int, description="Number of unique ads to return (default 50, max 100)"),
        ],
        responses={200: {"type": "object"}},
        description=(
            "Return the last N ads (unique by ad) that the current member viewed, ordered by the latest view time desc."
        ),
    )
    def get(self, request, *args, **kwargs):
        member = getattr(request.user, "member", request.user)
        try:
            limit = int(request.query_params.get("limit", 50))
        except (TypeError, ValueError):
            limit = 50
        limit = max(1, min(limit, 100))

        latest = (
            AdView.objects.filter(member=member)
            .values("ad")
            .annotate(viewed_at=Max("viewed_at"))
            .order_by("-viewed_at")[:limit]
        )
        ad_ids = [row["ad"] for row in latest]
        ad_map = {a.id: a for a in Ad.objects.filter(id__in=ad_ids)}

        items = []
        for row in latest:
            ad = ad_map.get(row["ad"])
            if not ad:
                continue
            items.append({"ad": AdListSerializer(ad).data, "viewed_at": row["viewed_at"]})

        return Response({"items": items}, status=status.HTTP_200_OK)


# -----------------------------
# Import pipeline endpoints (ViewSet)
# -----------------------------

class ImportViewSet(ViewSet):
    """Create import jobs (JWT required) and retrieve by id (public)."""

    authentication_classes = [MemberJWTAuthentication]

    def get_permissions(self):
        if getattr(self, "action", None) == "create":
            return [IsAuthenticated()]
        return [AllowAny()]

    @extend_schema(
        request=ImportRequestSerializer,
        responses={201: ImportJobSerializer},
        description=(
            "Create a new import job and attempt to import immediately. "
            "Respects remote site's limits and surfaces HTTP 429 with retry_after guidance."
        ),
    )
    def create(self, request):
        ser = ImportRequestSerializer(data=request.data)
        ser.is_valid(raise_exception=True)

        member = getattr(request.user, "member", request.user) if getattr(request.user, "is_authenticated", False) else None
        job = ImportJob.objects.create(member=member, url=ser.validated_data["url"], status="processing")
        try:
            job, _ad = import_listing_from_url(job.url, job.member)
        except LocalRateLimitError as e:
            job.status = "blocked"
            job.retry_after = int(e.seconds_left)
            job.message = "Local rate limit hit. Please retry later."
            job.save(update_fields=["status", "retry_after", "message", "updated_at"])
        return Response(ImportJobSerializer(job).data, status=status.HTTP_201_CREATED)

    @extend_schema(
        responses={200: ImportJobSerializer},
        description="Retrieve import job status by id.",
    )
    def retrieve(self, request, pk=None):
        job = get_object_or_404(ImportJob, pk=pk)
        return Response(ImportJobSerializer(job).data)
