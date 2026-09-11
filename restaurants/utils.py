import re
from restaurants.models import Tag

# ---------------------------------------------------------
# Preset Dictionaries & Whitelists
# ---------------------------------------------------------
MEAL_TYPES = [
    'Breakfast', 'Lunch', 'Dinner', 'Supper', 
    'Coffee Shop', 'Tea', 'Dessert', 'Noodle', 'Seafood', 'Kebab',
    'Steamboat', 'Tapas', 'Steak House'
]

DIETARY_OPTIONS = ['Halal', 'Vegetarian', 'No Pork No Lard', 'Vegan']

KNOWN_CUISINES = [
    'Malaysian', 'Japanese', 'Chinese', 'Indian', 'American', 
    'Italian', 'Mexican', 'Thai', 'Korean', 'Middle Eastern', 
    'Vietnamese', 'Malay', 'Yemeni', 'Persian', 'Arab', 'Jemenite'
]

SYNONYM_MAP = {
    'meal_type': {
        'Breakfast': ['breakfast', 'morning', 'roti', 'kaya', 'dim sum', 'bakery', 'kopitiam'],
        'Coffee Shop': ['cafe', 'coffee', 'kopi', 'tea', 'latte', 'espresso', 'starbucks'],
        'Noodle': ['noodle', 'ramen', 'laksa', 'mee', 'pho', 'pasta', 'bihun', 'kuey teow'],
        'Supper': ['supper', 'malam', '24 hours', '24h', 'late night', 'mamak'],
        'Seafood': ['seafood', 'fish', 'crab', 'prawn', 'lobster', 'squid', 'sotong', 'lala'],
        'Kebab': ['kebab', 'shawarma', 'falafel', 'gyro', 'doner'],
        'Steamboat': ['steamboat', 'hotpot', 'hot pot', 'lok lok', 'shabu shabu', 'haidilao', 'malatang'],
        'Tapas': ['tapas', 'small plates', 'pinchos', 'finger food'],
        'Steak House': ['steak', 'steakhouse', 'grill', 'ribs', 'beef', 'sirloin', 'wagyu'],
        'Barbecue': ['barbecue', 'bbq', 'roast', 'satay', 'yakiniku', 'samgyupsal', 'charcoal'],
        'Buffet': ['buffet', 'all you can eat', 'eat all you can'],
        'Fast Food': ['fast food', 'burger', 'fries', 'fried chicken', 'mcdonald', 'kfc'],
        'Bakery': ['bakery', 'bread', 'pastry', 'croissant', 'bakehouse', 'toast'],
        'Cafe': ['cafe', 'café', 'brunch', 'bistro'],
        'Pizza': ['pizza', 'pizzeria'],
    },
    'dietary': {
        'Halal': ['halal', 'muslim-friendly', 'restoran muslim', 'mamak', 'malay', 'arab', 'middle eastern'],
        'Vegetarian': ['vegetarian', 'vege', '素'],
        'No Pork No Lard': ['no pork', 'no lard', 'pork-free', 'pork free'],
        'Vegan': ['vegan', 'plant-based'],
    }
}


def apply_intelligent_tags(restaurant):
    """
    Intelligent Tagging Engine:
    1. Parses raw cuisine text and validates against whitelist to prevent UI pollution.
    2. Derives dietary and meal types via semantic keyword/synonym mapping (e.g., 'Mamak' -> Halal + Supper).
    3. Infers meal times based on operating hours.
    4. Categorizes unverified user inputs as 'other' to protect the main Cuisine UI.
    """
    raw_cuisine = getattr(restaurant, 'cuisine', '') or ''
    scanned_text = f"{restaurant.name} {raw_cuisine}".lower()

    # --- A. Cuisine Parsing & Safeguard Layer ---
    clean_raw = raw_cuisine.replace('_', ' ')
    tokens = re.split(r'[,/&;]|\band\b', clean_raw, flags=re.IGNORECASE)

    for token in tokens:
        c_name = token.strip().title()
        if not c_name:
            continue

        lower_c = c_name.lower()

        # Strict Categorization Logic
        if any(lower_c == m.lower() for m in MEAL_TYPES):
            correct_type = 'meal_type'
        elif any(lower_c == d.lower() for d in DIETARY_OPTIONS):
            correct_type = 'dietary'
        elif any(lower_c == kc.lower() for kc in KNOWN_CUISINES):
            correct_type = 'cuisine'
        else:
            # 🔴 Safeguard against dummy user input (e.g. 'cheap', 'sad', unknown tags)
            # Isolates unknown words as 'other' so they don't pollute the Cuisine UI header
            correct_type = 'other'

        tag, created = Tag.objects.get_or_create(
            name=c_name,
            defaults={'tag_type': correct_type}
        )

        # Force correct tag_type if previously misclassified
        if tag.tag_type != correct_type and correct_type != 'other':
            tag.tag_type = correct_type
            tag.save()

        tag.restaurants.add(restaurant)

    # --- B. Rule-Based & Synonym Mapping (Dietary) ---
    assigned_dietary = set()
    for tag_name, keywords in SYNONYM_MAP['dietary'].items():
        if any(kw in scanned_text for kw in keywords):
            assigned_dietary.add(tag_name)

    if not assigned_dietary:
        assigned_dietary.add('Halal')  # Local default fallback

    for d_name in assigned_dietary:
        d_tag, _ = Tag.objects.get_or_create(name=d_name, defaults={'tag_type': 'dietary'})
        d_tag.restaurants.add(restaurant)

    # --- C. Intelligent Meal Type Deduction ---
    assigned_meals = set()

    # 1) Time-Driven Deduction (From Opening Hours)
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

    # 2) Semantic Keyword Matching
    for tag_name, keywords in SYNONYM_MAP['meal_type'].items():
        if any(kw in scanned_text for kw in keywords):
            assigned_meals.add(tag_name)

    # 3) Deterministic Default Fallback
    if not assigned_meals:
        assigned_meals = {'Lunch', 'Dinner'}

    for m_name in assigned_meals:
        m_tag, _ = Tag.objects.get_or_create(name=m_name, defaults={'tag_type': 'meal_type'})
        m_tag.restaurants.add(restaurant)