import csv
import re
import random
from pathlib import Path
from django.core.management.base import BaseCommand
from restaurants.models import Restaurant, OpeningHour, Tag

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

        meal_types = [
            'Breakfast', 'Lunch', 'Dinner', 'Supper', 
            'Coffee Shop', 'Tea', 'Dessert', 'Noodle', 'Seafood', 'Kebab',
            'Steamboat', 'Tapas', 'Steak House', 'Barbecue', 'Buffet', 'Fast Food', 'Bakery', 'Cafe',
            'Pizza',
        ]
        dietary_options = ['Halal', 'Vegetarian', 'No Pork No Lard', 'Vegan']

        for name in meal_types:
            Tag.objects.get_or_create(name=name, tag_type='meal_type')
        for name in dietary_options:
            Tag.objects.get_or_create(name=name, tag_type='dietary')

        SYNONYM_MAP = {
            'meal_type': {
                'Breakfast': ['breakfast', 'morning', 'roti', 'kaya', 'dim sum', 'bakery', 'kopitiam'],
                'Coffee Shop': ['cafe', 'coffee', 'kopi', 'tea', 'latte', 'espresso', 'starbucks'],
                'Noodle': ['noodle', 'ramen', 'laksa', 'mee', 'pho', 'pasta', 'bihun', 'kuey teow'],
                'Supper': ['supper', 'malam', '24 hours', '24h', 'late night', 'mamak'],
            },
            'dietary': {
                'Halal': ['halal', 'muslim-friendly', 'restoran muslim', 'mamak', 'malay', 'arab', 'middle eastern'],
                'Vegetarian': ['vegetarian', 'vegan', 'vege', '素'],
            }
        }

        restaurants = Restaurant.objects.all()
        if not restaurants.exists():
            self.stdout.write(self.style.WARNING("No restaurants found! Please run seed_restaurants first."))
            return

        for restaurant in restaurants:
            raw_cuisine = getattr(restaurant, 'cuisine', '') or ''
            scanned_text = f"{restaurant.name} {raw_cuisine}".lower()
            
            # --- A. Cuisine Parsing ---
            clean_raw = raw_cuisine.replace('_', ' ')
            tokens = re.split(r'[,/&;]|\band\b', clean_raw, flags=re.IGNORECASE)
            for token in tokens:
                c_name = token.strip().title()
                if c_name:
                    if any(c_name.lower() == m.lower() for m in meal_types):
                        correct_type = 'meal_type'
                    elif any(c_name.lower() == d.lower() for d in dietary_options):
                        correct_type = 'dietary'
                    else:
                        correct_type = 'cuisine'

                    tag, created = Tag.objects.get_or_create(
                        name=c_name, 
                        defaults={'tag_type': correct_type}
                    )

                    if tag.tag_type != correct_type:
                        tag.tag_type = correct_type
                        tag.save()

                    tag.restaurants.add(restaurant)

            # --- B. Rule-Based & Synonym Mapping (Dietary) ---
            assigned_dietary = set()
            for tag_name, keywords in SYNONYM_MAP['dietary'].items():
                if any(kw in scanned_text for kw in keywords):
                    assigned_dietary.add(tag_name)
            
            if not assigned_dietary:
                assigned_dietary.add('Halal')

            for d_name in assigned_dietary:
                d_tag = Tag.objects.get(name=d_name, tag_type='dietary')
                d_tag.restaurants.add(restaurant)

            # --- C. Intelligent Meal Type Deduction ---
            assigned_meals = set()

            opening_hours = restaurant.hours.first()
            if opening_hours and opening_hours.opening_time and opening_hours.closing_time:
                open_h = opening_hours.opening_time.hour
                close_h = opening_hours.closing_time.hour

                if open_h <= 10:
                    assigned_meals.add('Breakfast')
                if open_h <= 14 and close_h >= 11:
                    assigned_meals.add('Lunch')
                if close_h >= 18 or close_h <= 4:
                    assigned_meals.add('Dinner')
                if close_h >= 22 or open_h >= 22 or close_h <= 4:
                    assigned_meals.add('Supper')

            for tag_name, keywords in SYNONYM_MAP['meal_type'].items():
                if any(kw in scanned_text for kw in keywords):
                    assigned_meals.add(tag_name)

            if not assigned_meals:
                assigned_meals = {'Lunch', 'Dinner'}

            for m_name in assigned_meals:
                m_tag = Tag.objects.get(name=m_name, tag_type='meal_type')
                m_tag.restaurants.add(restaurant)

        self.stdout.write(self.style.SUCCESS(f"Successfully tagged all {restaurants.count()} restaurants!"))