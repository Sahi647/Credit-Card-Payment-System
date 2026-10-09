from django.contrib.admin.models import ADDITION, LogEntry
from django.contrib.contenttypes.models import ContentType
from django.contrib import messages
from django.db import transaction
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods

from .forms import AdministratorCreationForm
from .roles import ADMINISTRATOR, assign_user_role


@require_http_methods(["GET", "POST"])
def create_administrator(request):
    form = AdministratorCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        with transaction.atomic():
            user = form.save(commit=False)
            user.email = form.cleaned_data["email"]
            user.save()
            assign_user_role(user, ADMINISTRATOR)
            LogEntry.objects.log_action(
                user_id=request.user.pk,
                content_type_id=ContentType.objects.get_for_model(user).pk,
                object_id=str(user.pk),
                object_repr=user.get_username(),
                action_flag=ADDITION,
                change_message=f"Created user with the {ADMINISTRATOR} role.",
            )
        messages.success(
            request,
            f"Administrator account '{user.get_username()}' was created.",
        )
        return redirect("admin:auth_user_changelist")

    return render(
        request,
        "admin/auth/user/create_administrator.html",
        {"form": form},
    )
