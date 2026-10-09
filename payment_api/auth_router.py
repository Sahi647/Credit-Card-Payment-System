from django.contrib.auth import authenticate
from fastapi import APIRouter, Form, HTTPException, status
from rest_framework_simplejwt.tokens import RefreshToken

auth_router = APIRouter(prefix="/api/auth", tags=["Authentication"])


@auth_router.post("/login/")
def oauth_login(username: str = Form(...), password: str = Form(...)):
    user = authenticate(
        username=username,
        password=password,
    )
    if user is None or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    refresh = RefreshToken.for_user(user)
    return {
        "access_token": str(refresh.access_token),
        "token_type": "bearer",
        "refresh_token": str(refresh),
    }
