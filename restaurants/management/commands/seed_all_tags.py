import re
import random
from django.core.management.base import BaseCommand
from restaurants.models import Tag
from restaurants.models import Restaurant

class Command(BaseCommand):
    help = "Parse cuisines and intelligently generate Meal Type & Dietary tags for all restaurants."

    def handle(self, *args, **options):

        # [Key New Feature]: First, clear all old tags in the database.
        Tag.objects.all().delete()

        # 1. Preset basic tags
        meal_types = ['Breakfast', 'Lunch', 'Dinner', 'Supper', 
                      'Coffee Shop', 'Tea', 'Dessert', 'Noodle', 'Seafood', 'Kebab']
        dietary_options = ['Halal', 'Vegetarian', 'No Pork No Lard', 'Vegan']

        for name in meal_types:
            Tag.objects.get_or_create(name=name, tag_type='meal_type')
        for name in dietary_options:
            Tag.objects.get_or_create(name=name, tag_type='dietary')

        restaurants = Restaurant.objects.all()
        if not restaurants.exists():
            self.stdout.write(self.style.WARNING("No restaurants found! Please run seed_restaurants first."))
            return

        for restaurant in restaurants:
            # --- Cuisine Parsing (Split Mixed Text) ---
            raw_cuisine = getattr(restaurant, 'cuisine', '')
            cuisines_found = []
            if raw_cuisine:
                clean_raw = raw_cuisine.replace('_', ' ')
                tokens = re.split(r'[,/&;]|\band\b', clean_raw, flags=re.IGNORECASE)
                for token in tokens:
                    c_name = token.strip().title()
                    if c_name:
                        # Intelligent classification determination
                        if c_name in meal_types:
                            correct_type = 'meal_type'
                        elif c_name in dietary_options:
                            correct_type = 'dietary'
                        else:
                            correct_type = 'cuisine'

                        tag, created = Tag.objects.get_or_create(
                            name=c_name, 
                            defaults={'tag_type': correct_type}
                        )

                        # If the label already exists but the type is incorrect 
                        # (e.g., old data was mistakenly classified as cuisine), correct it.
                        if not created and tag.tag_type != correct_type:
                            tag.tag_type = correct_type
                            tag.save()

                        tag.restaurants.add(restaurant)
                        if correct_type == 'cuisine':
                            cuisines_found.append(c_name.lower())

            # --- Dietary Rule Identification ---
            is_halal_suggested = any(k in ' '.join(cuisines_found) for k in ['malay', 'arab', 'indian', 'middle eastern', 'mamak'])
            if is_halal_suggested:
                halal_tag = Tag.objects.get(name='Halal', tag_type='dietary')
                halal_tag.restaurants.add(restaurant)
            else:
                random_dietary = random.choice(['Halal', 'No Pork No Lard', 'Vegetarian'])
                d_tag = Tag.objects.get(name=random_dietary, tag_type='dietary')
                d_tag.restaurants.add(restaurant)

            # --- Meal Type Rule Configuration ---
            assigned_meals = ['Lunch', 'Dinner']
            if random.choice([True, False]):
                assigned_meals.append('Breakfast')
            if random.choice([True, False]):
                assigned_meals.append('Supper')

            for m_name in assigned_meals:
                m_tag = Tag.objects.get(name=m_name, tag_type='meal_type')
                m_tag.restaurants.add(restaurant)

        self.stdout.write(self.style.SUCCESS(f"Successfully tagged all {restaurants.count()} restaurants!"))