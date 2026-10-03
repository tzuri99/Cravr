"""
Tagging Engine and Natural Language Processing (NLP) Rule-Based Ingestion System.

This module provides an automated, rule-based inference pipeline to categorize 
and tag restaurant instances dynamically based on raw user inputs, semantic 
synonym mappings, and temporal opening-hour constraints.

Key Features:
    - Whitelist validation to prevent User Interface (UI) pollution.
    - Automated taxonomy assignment (Meal Types, Dietary Flags, Cuisines).
    - Heuristic temporal inference based on operational time windows.
    - Fault-tolerant fallback strategies for missing or ambiguous metadata.
"""

import re
from typing import List, Dict, Set, Any
from restaurants.models import Tag, Restaurant


# =========================================================================
# System Taxonomy Whitelists & Reference Dictionaries
# =========================================================================

# Explicitly supported meal type categories for UI filtering
MEAL_TYPES: List[str] = [
    'Breakfast', 'Lunch', 'Dinner', 'Supper', 
    'Coffee Shop', 'Tea', 'Dessert', 'Noodle', 'Seafood', 'Kebab',
    'Steamboat', 'Tapas', 'Steak House'
]

# Standardized dietary constraint and compliance options
DIETARY_OPTIONS: List[str] = [
    'Halal', 'Vegetarian', 'No Pork No Lard', 'Vegan'
]

# Validated regional and national cuisine origins
KNOWN_CUISINES: List[str] = [
    'Malaysian', 'Japanese', 'Chinese', 'Indian', 'American', 
    'Italian', 'Mexican', 'Thai', 'Korean', 'Middle Eastern', 
    'Vietnamese', 'Malay', 'Yemeni', 'Persian', 'Arab', 'Jemenite'
]

# Semantic mapping matrix for token-based NLP keyword extraction
SYNONYM_MAP: Dict[str, Dict[str, List[str]]] = {
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


# =========================================================================
# Core Inference Pipeline
# =========================================================================

def apply_intelligent_tags(restaurant: Restaurant) -> None:
    """
    Executes the multi-stage automated tagging pipeline for a target restaurant.

    This function analyzes raw metadata (restaurant name, raw cuisine string, 
    and operational hours) to dynamically infer and attach `Tag` model 
    relational entities. It ensures system data integrity by enforcing strict 
    whitelisting and categorizing unrecognized terms into an isolated 'other' namespace.

    Processing Stages:
        1. Tokenization & Whitelist Validation (Cuisine Protection Layer).
        2. Rule-Based Keyword Extraction & Semantic Mapping (Dietary Restrictions).
        3. Temporal Operating Hour Analysis (Meal Schedule Deduction).
        4. Deterministic Fallback Assignment for Incomplete Metadata.

    Args:
        restaurant (Restaurant): The target Django model instance to process 
            and associate with verified tags.

    Returns:
        None: Modifies the relational Many-to-Many `restaurant.tags` mapping 
            in-place within the database.

    Raises:
        AttributeError: If required restaurant fields or relations are malformed.
    """
    # Extract raw attributes with safe string fallback
    raw_cuisine: str = getattr(restaurant, 'cuisine', '') or ''
    scanned_text: str = f"{restaurant.name} {raw_cuisine}".lower()

    # ---------------------------------------------------------------------
    # Phase A: Cuisine Parsing, Tokenization & Safeguard Layer
    # ---------------------------------------------------------------------
    # Standardize delimiting characters and split raw text into clean tokens
    clean_raw: str = raw_cuisine.replace('_', ' ')
    tokens: List[str] = re.split(r'[,/&;]|\band\b', clean_raw, flags=re.IGNORECASE)

    for token in tokens:
        c_name: str = token.strip().title()
        if not c_name:
            continue

        lower_c: str = c_name.lower()

        # Strict Multi-Category Taxonomical Evaluation
        if any(lower_c == m.lower() for m in MEAL_TYPES):
            correct_type: str = 'meal_type'
        elif any(lower_c == d.lower() for d in DIETARY_OPTIONS):
            correct_type: str = 'dietary'
        elif any(lower_c == kc.lower() for kc in KNOWN_CUISINES):
            correct_type: str = 'cuisine'
        else:
            # Safeguard Mechanism: Isolate unverified/arbitrary user tags (e.g., 'cheap', 'sad')
            # Prevents raw string pollution on primary UI category headers
            correct_type: str = 'other'

        # Atomic Retrieval or Creation of Tag Entity
        tag, created = Tag.objects.get_or_create(
            name=c_name,
            defaults={'tag_type': correct_type}
        )

        # Self-Correction Protocol: Update misclassified tags if taxonomy changed
        if tag.tag_type != correct_type and correct_type != 'other':
            tag.tag_type = correct_type
            tag.save()

        # Establish Relational Mapping
        tag.restaurants.add(restaurant)

    # ---------------------------------------------------------------------
    # Phase B: Rule-Based & Semantic Mapping (Dietary Compliance)
    # ---------------------------------------------------------------------
    assigned_dietary: Set[str] = set()

    # Match scanned text against predefined dietary synonym dictionaries
    for tag_name, keywords in SYNONYM_MAP['dietary'].items():
        if any(kw in scanned_text for kw in keywords):
            assigned_dietary.add(tag_name)

    # Contextual Fallback Policy (Default to Halal in local demographic context)
    if not assigned_dietary:
        assigned_dietary.add('Halal')

    # Batch associate derived dietary tags
    for d_name in assigned_dietary:
        d_tag, _ = Tag.objects.get_or_create(
            name=d_name, 
            defaults={'tag_type': 'dietary'}
        )
        d_tag.restaurants.add(restaurant)

    # ---------------------------------------------------------------------
    # Phase C: Intelligent Temporal Deductions (Meal Time Windows)
    # ---------------------------------------------------------------------
    assigned_meals: Set[str] = set()

    # 1. Temporal Deduction based on Operating Hours
    opening_hours = restaurant.hours.first()
    if opening_hours and opening_hours.opening_time and opening_hours.closing_time:
        open_h: int = opening_hours.opening_time.hour
        close_h: int = opening_hours.closing_time.hour

        # Morning Window Analysis (Opens before 10:00 AM)
        if open_h <= 10:
            assigned_meals.add('Breakfast')

        # Afternoon Window Analysis (Open across 11:00 AM - 2:00 PM)
        if open_h <= 14 and close_h >= 11:
            assigned_meals.add('Lunch')

        # Evening Window Analysis (Open past 6:00 PM or past midnight)
        if close_h >= 18 or close_h <= 4:
            assigned_meals.add('Dinner')

        # Late Night / Late Hours Window Analysis (Past 10:00 PM)
        if close_h >= 22 or open_h >= 22 or close_h <= 4:
            assigned_meals.add('Supper')

    # 2. Semantic Keyword Natural Language Deduction
    for tag_name, keywords in SYNONYM_MAP['meal_type'].items():
        if any(kw in scanned_text for kw in keywords):
            assigned_meals.add(tag_name)

    # 3. Deterministic Default Fallback Strategy
    if not assigned_meals:
        assigned_meals = {'Lunch', 'Dinner'}

    # Batch associate derived meal type tags
    for m_name in assigned_meals:
        m_tag, _ = Tag.objects.get_or_create(
            name=m_name, 
            defaults={'tag_type': 'meal_type'}
        )
        m_tag.restaurants.add(restaurant)