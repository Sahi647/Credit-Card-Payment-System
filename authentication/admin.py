from django.contrib import admin
from django.contrib.auth.models import User
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from django.contrib.admin.sites import NotRegistered
from django.utils.html import format_html, format_html_join

from .roles import ADMINISTRATOR, CUSTOMER, SUPPORT

try:
    admin.site.unregister(User)
except NotRegistered:
    pass


class UserAdmin(DjangoUserAdmin):
    change_list_template = "admin/auth/user/change_list.html"
    add_form_template = "admin/auth/user/add_form.html"
    list_display = (
        "username",
        "email",
        "role_badge",
        "active_badge",
        "date_joined",
    )
    list_filter = ("is_active", "is_staff", "groups", "date_joined")
    search_fields = ("username", "first_name", "last_name", "email")
    ordering = ("-date_joined",)
    list_per_page = 25

    @admin.display(description="Role")
    def role_badge(self, obj):
        role_colors = {
            ADMINISTRATOR: "administrator",
            SUPPORT: "support",
            CUSTOMER: "customer",
        }
        roles = list(obj.groups.values_list("name", flat=True))
        if obj.is_superuser and ADMINISTRATOR not in roles:
            roles.insert(0, ADMINISTRATOR)
        if not roles:
            return format_html('<span class="account-badge account-badge--unassigned">Unassigned</span>')
        badges = format_html_join(
            "",
            '<span class="account-badge account-badge--{}">{}</span>',
            (
                (
                    role_colors.get(role, "unassigned"),
                    role,
                )
                for role in roles
            ),
        )
        return format_html("{}", badges)

    @admin.display(description="Account status", boolean=False)
    def active_badge(self, obj):
        if obj.is_active:
            return format_html(
                '<span class="account-badge account-badge--active">Active</span>'
            )
        return format_html(
            '<span class="account-badge account-badge--inactive">Inactive</span>'
        )


admin.site.register(User, UserAdmin)
