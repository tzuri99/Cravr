import csv
from pathlib import Path
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant, OpeningHour, Tag
from restaurants.utils import apply_intelligent_tags, MEAL_TYPES, DIETARY_OPTIONS

class Command(BaseCommand):
    help = "Load restaurants from data/restaurants.csv and generate intelligent tags"

    def handle(self, *args, **options):
        # ---------------------------------------------------------
        # Part 1: Original seed_restaurants logic (UNCHANGED)
        # ---------------------------------------------------------
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
                        "is_approved": True,
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

        # ---------------------------------------------------------
        # Part 2: Intelligent Tag Generation Logic
        # ---------------------------------------------------------
        Tag.objects.all().delete()

        # 预创建基础 Tag 种类
        for name in MEAL_TYPES:
            Tag.objects.get_or_create(name=name, tag_type='meal_type')
        for name in DIETARY_OPTIONS:
            Tag.objects.get_or_create(name=name, tag_type='dietary')

        restaurants = Restaurant.objects.all()
        if not restaurants.exists():
            self.stdout.write(self.style.WARNING("No restaurants found! Please run seed_restaurants first."))
            return

        for restaurant in restaurants:
            apply_intelligent_tags(restaurant)

        self.stdout.write(self.style.SUCCESS(f"Successfully tagged all {restaurants.count()} restaurants!"))