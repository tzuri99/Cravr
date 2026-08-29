from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Restaurant, Tag
from .forms import RestaurantForm

def restaurant_list(request):
    # 1. Retrieve filter parameters from the URL (e.g., ?tag=1 or ?cuisine=...&tag=1)
    selected_tag_id = request.GET.get('tag')
    
    # 2. Search all restaurants
    restaurants = Restaurant.objects.all()
    if selected_tag_id:
        restaurants = restaurants.filter(tags__id=selected_tag_id).distinct()

    # 3. Search Tags grouped by type (for frontend layout)
    cuisine_tags = Tag.objects.filter(tag_type='cuisine')
    meal_type_tags = Tag.objects.filter(tag_type='meal_type')
    dietary_tags = Tag.objects.filter(tag_type='dietary')

    context = {
        'restaurants': restaurants,
        'cuisine_tags': cuisine_tags,
        'meal_type_tags': meal_type_tags,
        'dietary_tags': dietary_tags,
        'selected_tag_id': int(selected_tag_id) if selected_tag_id and selected_tag_id.isdigit() else None,
    }
    
    return render(request, "restaurants/restaurant_list.html", context)


def add_restaurant(request):
    if request.method == "POST":
        form = RestaurantForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Restaurant added.")
            return redirect("restaurant_list")
    else:
        form = RestaurantForm()

    return render(request, "restaurants/add_restaurant.html", {"form": form})