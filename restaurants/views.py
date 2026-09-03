import random
from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Restaurant, Tag
from .forms import RestaurantForm, OpeningHourFormSet


def restaurant_list(request):
    # 1. Retrieve individual category filter parameters from the URL
    selected_cuisine_id = request.GET.get('cuisine')
    selected_meal_id = request.GET.get('meal_type')
    selected_dietary_id = request.GET.get('dietary')
    
    # Legacy support for single tag parameter
    selected_tag_id = request.GET.get('tag')
    
    # 2. Filter restaurants iteratively based on selected criteria
    restaurants = Restaurant.objects.all()

    if selected_cuisine_id and selected_cuisine_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_cuisine_id))
        
    if selected_meal_id and selected_meal_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_meal_id))
        
    if selected_dietary_id and selected_dietary_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_dietary_id))

    # Backward compatibility filter for single 'tag' query param
    if selected_tag_id and selected_tag_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_tag_id))

    restaurants = restaurants.distinct()

    # 3. Fetch tags grouped by type for template rendering
    cuisine_tags = Tag.objects.filter(tag_type='cuisine')
    meal_type_tags = Tag.objects.filter(tag_type='meal_type')
    dietary_tags = Tag.objects.filter(tag_type='dietary')

    context = {
        'restaurants': restaurants,
        'cuisine_tags': cuisine_tags,
        'meal_type_tags': meal_type_tags,
        'dietary_tags': dietary_tags,
        'selected_cuisine_id': int(selected_cuisine_id) if selected_cuisine_id and selected_cuisine_id.isdigit() else None,
        'selected_meal_id': int(selected_meal_id) if selected_meal_id and selected_meal_id.isdigit() else None,
        'selected_dietary_id': int(selected_dietary_id) if selected_dietary_id and selected_dietary_id.isdigit() else None,
        'selected_tag_id': int(selected_tag_id) if selected_tag_id and selected_tag_id.isdigit() else None,
    }
    
    return render(request, "restaurants/restaurant_list.html", context)


def add_restaurant(request):
    # Preserved main branch logic with OpeningHourFormSet
    if request.method == "POST":
        form = RestaurantForm(request.POST)
        formset = OpeningHourFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            restaurant = form.save()
            formset.instance = restaurant
            formset.save()
            messages.success(request, "Restaurant added.")
            return redirect("restaurant_list")
    else:
        form = RestaurantForm()
        formset = OpeningHourFormSet(initial=[{"day": day} for day in range(7)])

    return render(
        request,
        "restaurants/add_restaurant.html",
        {"form": form, "formset": formset},
    )


def restaurant_picker(request):
    # Branch feature: Random restaurant selection logic
    cuisine_tags = Tag.objects.filter(tag_type__iexact='cuisine')
    meal_type_tags = Tag.objects.filter(tag_type__iexact='meal_type')
    dietary_tags = Tag.objects.filter(tag_type__iexact='dietary')

    selected_cuisine_id = request.GET.get('cuisine')
    selected_meal_id = request.GET.get('meal_type')
    selected_dietary_id = request.GET.get('dietary')

    # Start with all restaurants
    restaurants = Restaurant.objects.all()

    # Apply tag filters (AND logic)
    if selected_cuisine_id and selected_cuisine_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_cuisine_id))
        
    if selected_meal_id and selected_meal_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_meal_id))
        
    # Dietary restriction acts as a hard filter
    if selected_dietary_id and selected_dietary_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_dietary_id))

    restaurants = restaurants.distinct()

    # Random selection logic
    picked_restaurant = None
    no_matches = False

    # Trigger selection if form is submitted
    if request.GET:
        if restaurants.exists():
            picked_restaurant = random.choice(list(restaurants))
        else:
            no_matches = True

    context = {
        'cuisine_tags': cuisine_tags,
        'meal_type_tags': meal_type_tags,
        'dietary_tags': dietary_tags,
        'selected_cuisine_id': int(selected_cuisine_id) if selected_cuisine_id and selected_cuisine_id.isdigit() else None,
        'selected_meal_id': int(selected_meal_id) if selected_meal_id and selected_meal_id.isdigit() else None,
        'selected_dietary_id': int(selected_dietary_id) if selected_dietary_id and selected_dietary_id.isdigit() else None,
        'picked_restaurant': picked_restaurant,
        'no_matches': no_matches,
    }

    return render(request, 'restaurants/restaurant_picker.html', context)