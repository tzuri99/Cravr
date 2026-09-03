from django.db import models


class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=300, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    osm_id = models.BigIntegerField(unique=True, null=True, blank=True)

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