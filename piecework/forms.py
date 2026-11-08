from random import choice
from typing import ClassVar

from django import forms

from .models import HeightCategory, Note, Project, Unit, UnitSheetCount


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        exclude = ("started_on", "completed_on")


UnitSheetCountFormSet = forms.inlineformset_factory(
    Unit, UnitSheetCount, fields=("drywall_material", "count"), extra=1, can_delete=True
)


class NoteModelForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = "__all__"
        widgets: ClassVar = {
            "note": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Enter note here...",
                }
            )
        }


class UnitStatsFilterForm(forms.Form):
    project = forms.ModelChoiceField(
        queryset=Project.objects.order_by("name"),
        required=False,
        empty_label="All projects",
        widget=forms.Select(attrs={"class": "form-select"}),
    )

    height_feet = forms.ChoiceField(
        label="Height",
        required=False,
        choices=[("", "All heights"), *HeightCategory.choices],
        widget=forms.Select(attrs={"class": "form-select"}),
    )
