from django.contrib import admin
from .models import Action, ActionTime, SprintMethod, SprintTime, UnitArea, Unit

# Register your models here.
admin.site.register([Action, ActionTime, SprintMethod, SprintTime, UnitArea, Unit])
