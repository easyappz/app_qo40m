from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    HelloView,
    RegisterAPIView,
    LoginView,
    TokenRefreshView,
    MeAPIView,
)

router = DefaultRouter()

urlpatterns = [
    # Auth endpoints
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),

    # Current user endpoint
    path("me/", MeAPIView.as_view(), name="me"),

    # DRF router (future ViewSets will be registered here)
    path("", include(router.urls)),

    # Existing hello endpoint
    path("hello/", HelloView.as_view(), name="hello"),
]
