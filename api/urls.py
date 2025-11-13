from django.urls import path, include
from rest_framework.routers import DefaultRouter

from .views import (
    HelloView,
    RegisterAPIView,
    LoginView,
    TokenRefreshView,
    MeAPIView,
    AdsPopularAPIView,
    AdDetailAPIView,
    RateAdAPIView,
    ToggleFavoriteAPIView,
    MyFavoritesAPIView,
    MyAdsAPIView,
)

router = DefaultRouter()

urlpatterns = [
    # Auth endpoints
    path("auth/register/", RegisterAPIView.as_view(), name="auth-register"),
    path("auth/login/", LoginView.as_view(), name="auth-login"),
    path("auth/refresh/", TokenRefreshView.as_view(), name="auth-refresh"),

    # Current user endpoint
    path("me/", MeAPIView.as_view(), name="me"),

    # Ads endpoints
    path("ads/popular/", AdsPopularAPIView.as_view(), name="ads-popular"),
    path("ads/<int:ad_id>/", AdDetailAPIView.as_view(), name="ad-detail"),
    path("ads/<int:ad_id>/ratings/", RateAdAPIView.as_view(), name="ad-rate"),
    path("ads/<int:ad_id>/favorite/", ToggleFavoriteAPIView.as_view(), name="ad-favorite-toggle"),
    path("me/favorites/", MyFavoritesAPIView.as_view(), name="me-favorites"),
    path("me/ads/", MyAdsAPIView.as_view(), name="me-ads"),

    # DRF router (future ViewSets will be registered here)
    path("", include(router.urls)),

    # Existing hello endpoint
    path("hello/", HelloView.as_view(), name="hello"),
]
