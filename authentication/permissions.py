from rest_framework.permissions import BasePermission

from .roles import CUSTOMER, has_role


class IsCustomer(BasePermission):
    message = "An assigned Customer role is required."

    def has_permission(self, request, view):
        return has_role(request.user, CUSTOMER)
