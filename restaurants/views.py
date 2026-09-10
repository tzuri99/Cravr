import random
from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404
from .models import Restaurant, Tag, Wishlist
from .forms import RestaurantForm, OpeningHourFormSet
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from restaurants.utils import apply_intelligent_tags


def restaurant_list(request):
    # 1. Retrieve individual category filter parameters from the URL
    selected_cuisine_id = request.GET.get('cuisine')
    selected_meal_id = request.GET.get('meal_type')
    selected_dietary_id = request.GET.get('dietary')
    
    # Legacy support for single tag parameter
    selected_tag_id = request.GET.get('tag')
    
    # 2. Filter restaurants iteratively based on selected criteria
    restaurants = Restaurant.objects.filter(is_approved=True)

    query = request.GET.get('q', '').strip()
    if query:
        restaurants = restaurants.filter(name__icontains=query) | restaurants.filter(address__icontains=query)

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

    if request.user.is_authenticated:
        pending_restaurants = Restaurant.objects.filter(added_by=request.user, is_approved=False)
        # Fetch IDs of restaurants bookmarked by current user
        user_wishlist_ids = list(Wishlist.objects.filter(user=request.user).values_list('restaurant_id', flat=True))
    else:
        pending_restaurants = []
        user_wishlist_ids = []

    context = {
        'restaurants': restaurants,
        'cuisine_tags': cuisine_tags,
        'meal_type_tags': meal_type_tags,
        'dietary_tags': dietary_tags,
        'selected_cuisine_id': int(selected_cuisine_id) if selected_cuisine_id and selected_cuisine_id.isdigit() else None,
        'selected_meal_id': int(selected_meal_id) if selected_meal_id and selected_meal_id.isdigit() else None,
        'selected_dietary_id': int(selected_dietary_id) if selected_dietary_id and selected_dietary_id.isdigit() else None,
        'selected_tag_id': int(selected_tag_id) if selected_tag_id and selected_tag_id.isdigit() else None,
        'pending_restaurants': pending_restaurants,
        'user_wishlist_ids': user_wishlist_ids,
        'query': query,
    }
    
    return render(request, "restaurants/restaurant_list.html", context)


@login_required
def add_restaurant(request):
    if request.method == "POST":
        form = RestaurantForm(request.POST)
        formset = OpeningHourFormSet(request.POST)

        if form.is_valid() and formset.is_valid():
            restaurant = form.save(commit=False)
            restaurant.added_by = request.user
            restaurant.is_approved = False
            restaurant.save()
            formset.instance = restaurant
            formset.save()
            apply_intelligent_tags(restaurant)
            messages.success(request, "Restaurant submitted. It will be visible once approved.")
            return redirect("restaurant_list")
    else:
        form = RestaurantForm()
        formset = OpeningHourFormSet(initial=[{"day": day} for day in range(7)])

    return render(request, "restaurants/add_restaurant.html", {"form": form, "formset": formset})


def restaurant_picker(request):
    # Branch feature: Random restaurant selection logic
    cuisine_tags = Tag.objects.filter(tag_type__iexact='cuisine')
    meal_type_tags = Tag.objects.filter(tag_type__iexact='meal_type')
    dietary_tags = Tag.objects.filter(tag_type__iexact='dietary')

    selected_cuisine_id = request.GET.get('cuisine')
    selected_meal_id = request.GET.get('meal_type')
    selected_dietary_id = request.GET.get('dietary')

    # Start with all restaurants
    restaurants = Restaurant.objects.filter(is_approved=True)

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


@login_required
def toggle_wishlist(request, restaurant_id):
    """Add or remove restaurant from user's wishlist."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, restaurant=restaurant).first()

    if wishlist_item:
        wishlist_item.delete()
        messages.info(request, f"Removed {restaurant.name} from your wishlist.")
    else:
        Wishlist.objects.get_or_create(user=request.user, restaurant=restaurant)
        messages.success(request, f"Added {restaurant.name} to your wishlist!")

    return redirect(request.META.get('HTTP_REFERER', 'restaurant_list'))


@login_required
def wishlist_list(request):
    """Display user's wishlisted restaurants."""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('restaurant')
    return render(request, 'restaurants/wishlist.html', {'wishlist_items': wishlist_items})


def restaurants_json(request):
    data = [
        {
            "id": r.id,
            "name": r.name,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "cuisine": r.cuisine,
            "address": r.address,
        }
        for r in Restaurant.objects.filter(is_approved=True)
    ]
    return JsonResponse(data, safe=False)


def map_view(request):
    return render(request, "restaurants/map.html")