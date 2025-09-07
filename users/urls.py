from django.urls import path
from rest_framework.permissions import AllowAny
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView

from users.apps import UsersConfig
from users.views import (
    PaymentViewSet,
    UserCreateAPIView,
    UserDeleteAPIView,
    UserListAPIView,
    UserRetrieveAPIView,
    UserUpdateAPIView,
    SubscriptionAPIView,
)

app_name = UsersConfig.name

router = DefaultRouter()
router.register(r"payments", PaymentViewSet, basename="payments")

urlpatterns = [
    path("list/", UserListAPIView.as_view(), name="users_list"),
    path("profile/<int:pk>/", UserRetrieveAPIView.as_view(), name="profile"),
    path("profile/update/", UserUpdateAPIView.as_view(), name="profile_update"),
    path("profile/delete/", UserDeleteAPIView.as_view(), name="profile_delete"),
    path("register/", UserCreateAPIView.as_view(), name="register"),
    path(
        "login/",
        TokenObtainPairView.as_view(permission_classes=[AllowAny]),
        name="login",
    ),
    path(
        "token/refresh/",
        TokenRefreshView.as_view(permission_classes=[AllowAny]),
        name="token_refresh",
    ),
    path("subscriptions/", SubscriptionAPIView.as_view(), name="subscriptions"),
] + router.urls
