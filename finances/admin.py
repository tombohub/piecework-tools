from django.contrib import admin

from .models import Item, RecurringExpense, Vendor

admin.site.register([Item, Vendor, RecurringExpense])
