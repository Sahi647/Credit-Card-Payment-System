"""
ASGI config for Credit_Card project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.1/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from starlette.applications import Starlette
from starlette.routing import Mount

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'Credit_Card.settings')

django_application = get_asgi_application()

from payment_api.main import app as payment_application

application = Starlette(
    routes=[
        Mount("/payment", app=payment_application),
        Mount("/", app=django_application),
    ]
)
