from django import forms

from .models import Note, Unit, UnitSheetCount


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = "__all__"


UnitSheetCountFormSet = forms.inlineformset_factory(
    Unit, UnitSheetCount, fields=("drywall_material", "count"), extra=1, can_delete=True
)


class NoteModelForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = "__all__"
        widgets = {
            "note": forms.Textarea(
                attrs={
                    "rows": 2,
                    "class": "form-control",
                    "placeholder": "Enter note here...",
                }
            )
        }
