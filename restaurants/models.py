from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=255)
    cuisine = models.CharField(max_length=255, blank=True, null=True)
    address = models.CharField(max_length=255, blank=True, null=True)
    latitude = models.FloatField(blank=True, null=True)
    longitude = models.FloatField(blank=True, null=True)
    opening_time = models.TimeField(blank=True, null=True)
    closing_time = models.TimeField(blank=True, null=True)

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