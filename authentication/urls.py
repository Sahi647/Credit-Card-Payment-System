from django.urls import path
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import RegisterView, LogoutView, ProfileView, register_page, login_page, profile_page, logout_page

urlpatterns = [
    path("register/", RegisterView.as_view(), name="auth_register"),
    path("login/", TokenObtainPairView.as_view(), name="auth_login"),
    path("refresh/", TokenRefreshView.as_view(), name="auth_refresh"),
    path("logout/", LogoutView.as_view(), name="auth_logout"),
    path("profile/", ProfileView.as_view(), name="auth_profile"),
    path("web/register/", register_page, name="auth_register_page"),
    path("web/login/", login_page, name="auth_login_page"),
    path("web/profile/", profile_page, name="auth_profile_page"),
    path("web/logout/", logout_page, name="auth_logout_page"),
]