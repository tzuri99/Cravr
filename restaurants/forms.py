from django import forms
from .models import Restaurant


class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name", "latitude", "longitude", "address", "cuisine", "opening_time", "closing_time"]
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }