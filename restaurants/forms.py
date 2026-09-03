from django import forms
from django.forms import inlineformset_factory
from .models import Restaurant, OpeningHour

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name", "latitude", "longitude", "address", "cuisine"]

OpeningHourFormSet = inlineformset_factory(
    Restaurant,
    OpeningHour,
    fields=["day", "opening_time", "closing_time", "is_closed"],
    widgets={
        "opening_time": forms.TimeInput(attrs={"type": "time"}),
        "closing_time": forms.TimeInput(attrs={"type": "time"}),
    },
    extra=7,
    max_num=7,
    can_delete=False,
)