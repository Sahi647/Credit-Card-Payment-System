from django.contrib import admin
from authentication.roles import ADMINISTRATOR, SUPPORT, has_role
from .models import Card

admin.site.site_header = "CardFlow | Administration"
admin.site.site_title = "CardFlow Admin"
admin.site.index_title = "Operations dashboard"


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "card_type", "masked_number", "last_four", "expiry", "created_at")
    list_filter = ("card_type", "created_at")
    search_fields = ("user__username", "card_holder", "last_four")
    readonly_fields = ("masked_number", "last_four", "created_at")

    def has_module_permission(self, request):
        return has_role(request.user, ADMINISTRATOR) or has_role(request.user, SUPPORT)

    def has_view_permission(self, request, obj=None):
        return has_role(request.user, ADMINISTRATOR) or has_role(request.user, SUPPORT)

    def has_add_permission(self, request):
        return has_role(request.user, ADMINISTRATOR)

    def has_change_permission(self, request, obj=None):
        return has_role(request.user, ADMINISTRATOR)

    def has_delete_permission(self, request, obj=None):
        return has_role(request.user, ADMINISTRATOR)