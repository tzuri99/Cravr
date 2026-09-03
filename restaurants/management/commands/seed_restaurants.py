import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant, OpeningHour

class Command(BaseCommand):
    help = "Load restaurants from data/restaurants.csv"

    def handle(self, *args, **options):
        csv_path = Path("data/restaurants.csv")
        created = 0

        with open(csv_path, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                restaurant, was_new = Restaurant.objects.get_or_create(
                    name=row["name"],
                    defaults={
                        "latitude": float(row["latitude"]),
                        "longitude": float(row["longitude"]),
                        "address": row.get("address", ""),
                        "cuisine": row.get("cuisine", ""),
                    },
                )

                if was_new:
                    created += 1
                    opening = row.get("opening_time") or None
                    closing = row.get("closing_time") or None
                    for day in range(7):
                        OpeningHour.objects.create(
                            restaurant=restaurant,
                            day=day,
                            opening_time=opening,
                            closing_time=closing,
                        )

        self.stdout.write(self.style.SUCCESS(f"Added {created} restaurants"))