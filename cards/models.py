from django.db import models
from django.contrib.auth.models import User


class Card(models.Model):
    CARD_TYPES = [("Credit", "Credit"), ("Debit", "Debit"), ("Premium", "Premium")]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="cards")
    card_type = models.CharField(max_length=20, choices=CARD_TYPES, default="Credit")
    card_holder = models.CharField(max_length=100)
    masked_number = models.CharField(max_length=19)
    last_four = models.CharField(max_length=4)
    expiry = models.CharField(max_length=5)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_type} **** {self.last_four}"