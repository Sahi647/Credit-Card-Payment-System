import os

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jwt import InvalidTokenError, decode
from sqlalchemy import text
from sqlalchemy.orm import Session

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "Credit_Card.settings")
from django.conf import settings

from .database import get_db
from authentication.roles import ADMINISTRATOR

oauth2_scheme = OAuth2PasswordBearer(
    tokenUrl="/api/auth/login/",
    auto_error=False,
)


def get_current_user_id(
    token: str | None = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> int:
    unauthorized = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="A valid access token is required.",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if token is None:
        raise unauthorized

    try:
        claims = decode(
            token,
            settings.SECRET_KEY,
            algorithms=["HS256"],
        )
        user_id = int(claims["user_id"])
        if claims.get("token_type") != "access" or user_id < 1:
            raise unauthorized
    except (InvalidTokenError, KeyError, TypeError, ValueError):
        raise unauthorized from None

    user = db.execute(
        text("SELECT is_active FROM auth_user WHERE id = :user_id"),
        {"user_id": user_id},
    ).mappings().first()
    if not user or not user["is_active"]:
        raise unauthorized
    return user_id


def require_roles(*allowed_roles):
    def check_role(
        user_id: int = Depends(get_current_user_id),
        db: Session = Depends(get_db),
    ) -> int:
        memberships = db.execute(
            text(
                """
                SELECT u.is_superuser, auth_group.name AS role_name
                FROM auth_user AS u
                LEFT JOIN auth_user_groups AS membership ON membership.user_id = u.id
                LEFT JOIN auth_group ON auth_group.id = membership.group_id
                WHERE u.id = :user_id
                """
            ),
            {"user_id": user_id},
        ).mappings().all()
        if not memberships:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="The account no longer exists.",
            )
        is_superuser = any(row["is_superuser"] for row in memberships)
        assigned_roles = {row["role_name"] for row in memberships if row["role_name"]}
        if not (
            (ADMINISTRATOR in allowed_roles and is_superuser)
            or assigned_roles.intersection(allowed_roles)
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your assigned role does not permit this operation.",
            )
        return user_id

    return check_role
