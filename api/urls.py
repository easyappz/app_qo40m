from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status

from .views import HelloView

router = DefaultRouter()
# Router scaffold (to be filled later):
# router.register(r"ads", AdsViewSet, basename="ad")
# router.register(r"comments", CommentViewSet, basename="comment")


class RegisterView(APIView):
    def post(self, request, *args, **kwargs):
        return Response({"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class LoginView(APIView):
    def post(self, request, *args, **kwargs):
        return Response({"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class TokenRefreshView(APIView):
    def post(self, request, *args, **kwargs):
        return Response({"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class MeView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"detail": "Not implemented"}, status=status.HTTP_501_NOT_IMPLEMENTED)


class AdsPlaceholderView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"results": [], "detail": "Ads placeholder"}, status=status.HTTP_200_OK)


class CommentsPlaceholderView(APIView):
    def get(self, request, *args, **kwargs):
        return Response({"results": [], "detail": "Comments placeholder"}, status=status.HTTP_200_OK)


urlpatterns = [
    # Auth endpoints (placeholders)
    path("auth/register/", RegisterView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),

    # Current user endpoint (placeholder)
    path("me/", MeView.as_view(), name="me"),

    # Group endpoints placeholders
    path("ads/", AdsPlaceholderView.as_view(), name="ads-list"),
    path("comments/", CommentsPlaceholderView.as_view(), name="comments-list"),

    # DRF router (future ViewSets will be registered here)
    path("", include(router.urls)),

    # Existing hello endpoint
    path("hello/", HelloView.as_view(), name="hello"),
]
