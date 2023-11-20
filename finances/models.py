from django.db import models


class BaseModel(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class Item(BaseModel):
    """
    Purchased item or service
    """

    name = models.CharField(max_length=50)

    def __str__(self):
        return str(self.name)


class Vendor(BaseModel):
    """
    Store or provider of service
    """

    name = models.CharField(max_length=255)
    items = models.ManyToManyField(Item)

    def __str__(self):
        return str(self.name)


class RecurringExpense(BaseModel):
    """
    Expenses ocurring on regular basis, like subscriptions, rent etc
    """

    FREQUENCY_CHOICES = [
        ("weekly", "Weekly"),
        ("monthly", "Monthly"),
        ("yearly", "Yearly"),
    ]

    name = models.CharField(max_length=100)
    item = models.ForeignKey(Item, on_delete=models.PROTECT)
    frequency = models.CharField(max_length=20, choices=FREQUENCY_CHOICES)
    aproximate_amount = models.DecimalField(max_digits=6, decimal_places=2)

    def __str__(self):
        return str(self.name)
