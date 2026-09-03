from django import forms
from django.forms import inlineformset_factory
from .models import Restaurant, OpeningHour

class RestaurantForm(forms.ModelForm):
    class Meta:
        model = Restaurant
        fields = ["name", "latitude", "longitude", "address", "cuisine"]

class OpeningHourForm(forms.ModelForm):
    class Meta:
        model = OpeningHour
        fields = ["day", "opening_time", "closing_time", "is_closed"]
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        cleaned_data = super().clean()
        is_closed = cleaned_data.get("is_closed")
        opening = cleaned_data.get("opening_time")
        closing = cleaned_data.get("closing_time")

        if is_closed:
            cleaned_data["opening_time"] = None
            cleaned_data["closing_time"] = None
        elif opening and closing and closing <= opening:
            raise forms.ValidationError("Closing time must be after opening time.")

        return cleaned_data

OpeningHourFormSet = inlineformset_factory(
    Restaurant,
    OpeningHour,
    form=OpeningHourForm,
    extra=7,
    max_num=7,
    can_delete=False,
)