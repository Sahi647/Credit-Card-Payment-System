from functools import wraps

from django.contrib.auth.models import Group, Permission
from django.shortcuts import redirect

ADMINISTRATOR = "Administrator"
SUPPORT = "Support"
CUSTOMER = "Customer"
ROLE_NAMES = (ADMINISTRATOR, SUPPORT, CUSTOMER)


def has_role(user, role):
    if not user.is_authenticated or not user.is_active:
        return False
    if role == ADMINISTRATOR and user.is_superuser:
        return True
    return user.groups.filter(name=role).exists()


def is_administrator(user):
    return has_role(user, ADMINISTRATOR)


def assign_user_role(user, role):
    if role not in ROLE_NAMES:
        raise ValueError(f"Unknown role: {role}")
    group, _ = Group.objects.get_or_create(name=role)
    user.groups.clear()
    user.groups.add(group)
    for permission_cache in ("_perm_cache", "_group_perm_cache", "_user_perm_cache"):
        user.__dict__.pop(permission_cache, None)
    if not user.is_superuser:
        user.is_staff = role in (ADMINISTRATOR, SUPPORT)
        user.save(update_fields=["is_staff"])


def role_required(role):
    def decorator(view_func):
        @wraps(view_func)
        def wrapped(request, *args, **kwargs):
            from django.core.exceptions import PermissionDenied

            if not request.user.is_authenticated:
                return redirect("auth_login_page")
            if (
                role == CUSTOMER
                and request.user.is_active
                and not request.user.is_staff
                and not request.user.is_superuser
                and not request.user.groups.exists()
            ):
                assign_user_role(request.user, CUSTOMER)
            if not has_role(request.user, role):
                raise PermissionDenied
            return view_func(request, *args, **kwargs)

        return wrapped

    return decorator


def create_role_groups():
    groups = {name: Group.objects.get_or_create(name=name)[0] for name in ROLE_NAMES}

    groups[ADMINISTRATOR].permissions.set(Permission.objects.all())
    groups[SUPPORT].permissions.set(
        Permission.objects.filter(
            content_type__app_label__in=("cards", "transactions"),
            codename__startswith="view_",
        )
    )

    groups[CUSTOMER].permissions.clear()


def initialize_roles(sender, **kwargs):
    create_role_groups()
