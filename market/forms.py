from django import forms
from .models import WatchItem


class WatchItemCreateForm(forms.ModelForm):
    class Meta:
        model = WatchItem
        fields = ["target_price", "preferred_condition", "region", "is_active"]
