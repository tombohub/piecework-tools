from random import choice
from typing import ClassVar

from django import forms

from .models import (
    BoardingSprint,
    HeightCategory,
    Note,
    Project,
    Unit,
    UnitArea,
    UnitSheetCount,
)


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


class BoardingSprintResultsForm(forms.ModelForm):
    unit_area = forms.ModelChoiceField(
        label="Unit area",
        queryset=UnitArea.objects.order_by("name"),
        required=False,
        empty_label="Select area",
        widget=forms.Select(
            attrs={
                "class": "form-select",
                "autofocus": True,
            }
        ),
    )
    piece_count = forms.IntegerField(
        label="Pieces installed",
        min_value=1,
        widget=forms.NumberInput(
            attrs={
                "class": "form-control",
                "min": 1,
            }
        ),
    )

    class Meta:
        model = BoardingSprint
        fields = ("unit_area", "piece_count")

