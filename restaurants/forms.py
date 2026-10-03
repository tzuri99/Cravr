from django import forms
from django.forms import inlineformset_factory
from .models import Restaurant, OpeningHour, Review, ReviewPhoto


class RestaurantForm(forms.ModelForm):
    class Meta:
        # Generate the form from the Restaurant model
        model = Restaurant

        # added_by and is_approved are handled automatically in the view
        fields = ["name", "latitude", "longitude", "address", "cuisine"]


class OpeningHourForm(forms.ModelForm):
    class Meta:
        # Generate the form from the OpeningHour model
        model = OpeningHour
        fields = ["day", "opening_time", "closing_time", "is_closed"]

        # Use browser-native time picker inputs
        widgets = {
            "opening_time": forms.TimeInput(attrs={"type": "time"}),
            "closing_time": forms.TimeInput(attrs={"type": "time"}),
        }

    def clean(self):
        # Run Django's built-in validation first
        cleaned_data = super().clean()

        # Retrieve the validated field values
        is_closed = cleaned_data.get("is_closed")
        opening = cleaned_data.get("opening_time")
        closing = cleaned_data.get("closing_time")

        # Clear the time fields when the restaurant is marked as closed
        if is_closed:
            cleaned_data["opening_time"] = None
            cleaned_data["closing_time"] = None

        # Otherwise make sure the closing time is later than the opening time
        elif opening and closing and closing <= opening:
            raise forms.ValidationError("Closing time must be after opening time.")

        # Return the validated and possibly adjusted data
        return cleaned_data


# Create multiple OpeningHourForm entries linked to one Restaurant with a maximum of 7 rows, one for each day of the week
OpeningHourFormSet = inlineformset_factory(
    Restaurant,
    OpeningHour,
    form=OpeningHourForm,
    extra=7,
    max_num=7,
    can_delete=False,
)


class ReviewForm(forms.ModelForm):
    # Replace the default rating select box with five star radio options
    stars = forms.TypedChoiceField(
        choices=[
            (1, "★"),
            (2, "★"),
            (3, "★"),
            (4, "★"),
            (5, "★"),
        ],
        widget=forms.RadioSelect,

        # Convert the submitted value from a string to an integer
        coerce=int,

        # Require the user to choose a rating
        required=True,
    )

    class Meta:
        model = Review

        # Photos are processed separately through request.FILES
        fields = ["stars", "text"]

        # Customise the appearance of the review text area
        widgets = {
            "text": forms.Textarea(
                attrs={
                    "rows": 4,
                    "placeholder": "Share your thoughts..."
                }
            ),
        }