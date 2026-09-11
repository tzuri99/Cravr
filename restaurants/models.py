from django.conf import settings
from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=300, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    osm_id = models.BigIntegerField(unique=True, null=True, blank=True)

    added_by = models.ForeignKey(
        "auth.User", null=True, blank=True, on_delete=models.SET_NULL, related_name="restaurants_added"
    )
    is_approved = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name


class Tag(models.Model):
    TAG_TYPES = (
        ('cuisine', 'Cuisine'),
        ('meal_type', 'Meal Type'),
        ('dietary', 'Dietary Info'),
    )

    name = models.CharField(max_length=50)
    tag_type = models.CharField(max_length=20, choices=TAG_TYPES, default='cuisine')
    restaurants = models.ManyToManyField(Restaurant, related_name='tags', blank=True)

    def __str__(self):
        return f"{self.name} ({self.get_tag_type_display()})"


class OpeningHour(models.Model):
    DAYS = [
        (0, "Monday"),
        (1, "Tuesday"),
        (2, "Wednesday"),
        (3, "Thursday"),
        (4, "Friday"),
        (5, "Saturday"),
        (6, "Sunday"),
    ]

    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name="hours")
    day = models.IntegerField(choices=DAYS)
    opening_time = models.TimeField(null=True, blank=True)
    closing_time = models.TimeField(null=True, blank=True)
    is_closed = models.BooleanField(default=False)

    class Meta:
        ordering = ["day"]

    def __str__(self):
        return f"{self.restaurant.name} {self.get_day_display()}"

class Review(models.Model):
    restaurant = models.ForeignKey(
        Restaurant, on_delete=models.CASCADE, related_name="reviews"
    )
    author = models.ForeignKey(
        "auth.User", on_delete=models.CASCADE, related_name="reviews"
    )
    stars = models.IntegerField(choices=[(i, str(i)) for i in range(1, 6)])
    text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        unique_together = ("restaurant", "author")

    def __str__(self):
        return f"{self.stars}\u2605 {self.restaurant.name}"

class Wishlist(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='wishlist')
    restaurant = models.ForeignKey(Restaurant, on_delete=models.CASCADE, related_name='wishlisted_by')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'restaurant')

    def __str__(self):
        return f"{self.user.username} - {self.restaurant.name}"