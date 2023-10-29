from django import forms
from .models import Unit, Note


class UnitForm(forms.ModelForm):
    class Meta:
        model = Unit
        fields = "__all__"

class NoteModelForm(forms.ModelForm):
    class Meta:
        model = Note
        fields = '__all__'
        widgets = {
            'note': forms.Textarea(attrs={'rows': 2, 'class': 'form-control', 'placeholder': 'Enter note here...'})}
