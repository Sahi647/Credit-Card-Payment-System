from django.db import models


class Transaction(models.Model):
    transaction_id = models.CharField(max_length=50, unique=True)
    user_id = models.IntegerField()
    payment_id = models.CharField(max_length=50)
    card_id = models.IntegerField()
    card_last_four = models.CharField(max_length=4)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    status = models.CharField(max_length=20)
    created_at = models.DateTimeField()

    class Meta:
        db_table = "transactions"
        managed = False
        ordering = ["-created_at"]

    def __str__(self):
        return self.transaction_id