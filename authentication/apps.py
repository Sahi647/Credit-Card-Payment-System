from django.apps import AppConfig


class AuthenticationConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "authentication"

    def ready(self):
        from django.db.models.signals import post_migrate

        from .roles import initialize_roles

        post_migrate.connect(
            initialize_roles,
            dispatch_uid="authentication.create_role_groups",
        )
