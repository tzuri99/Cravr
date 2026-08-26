import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant


class Command(BaseCommand):
    help = "Load restaurants from data/restaurants.csv"

    def handle(self, *args, **options):
        csv_path = Path("data/restaurants.csv")
        created = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                obj, was_new = Restaurant.objects.get_or_create(
                    name=row["name"],
                    defaults={
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "address": row.get("address", ""),
                        "cuisine": row.get("cuisine", ""),
                        "opening_hours": row.get("opening_hours", ""),
                    },
                )
                if was_new:
                    created += 1

        self.stdout.write(self.style.SUCCESS(f"Added {created} restaurants"))