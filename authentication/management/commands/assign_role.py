from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError

from authentication.roles import ROLE_NAMES, assign_user_role, create_role_groups


class Command(BaseCommand):
    help = "Assign a user one application role: Administrator, Support, or Customer."

    def add_arguments(self, parser):
        parser.add_argument("username")
        parser.add_argument("role", choices=ROLE_NAMES)

    def handle(self, *args, **options):
        create_role_groups()
        user_model = get_user_model()
        try:
            user = user_model.objects.get(username=options["username"])
        except user_model.DoesNotExist as error:
            raise CommandError(
                f"User '{options['username']}' does not exist."
            ) from error

        role = options["role"]
        assign_user_role(user, role)
        self.stdout.write(
            self.style.SUCCESS(f"Assigned {role} role to {user.get_username()}.")
        )
        if role == "Customer":
            self.stdout.write("The account has no Django Admin access.")
        else:
            self.stdout.write("The account can now sign in to Django Admin.")
