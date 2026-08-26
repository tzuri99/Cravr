from django.db import models

class Restaurant(models.Model):
    name = models.CharField(max_length=200)
    latitude = models.FloatField()
    longitude = models.FloatField()
    address = models.CharField(max_length=300, blank=True)
    cuisine = models.CharField(max_length=100, blank=True)
    opening_hours = models.CharField(max_length=200, blank=True)
    osm_id = models.BigIntegerField(unique=True, null=True, blank=True)

    def __str__(self):
        return self.name