import math
import random
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render

from .forms import OpeningHourFormSet, RestaurantForm, ReviewForm
from .models import Restaurant, Review, Tag, Wishlist
from restaurants.utils import apply_intelligent_tags


def calculate_haversine_distance(lat1, lon1, lat2, lon2):
    # Calculate the great-circle distance between two sets of latitude and longitude coordinates using the haversine formula (unit: kilometers).
    R = 6371.0  # Earth's average radius (kilometers)
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return R * c


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

    # Wishlist filter: Check if user toggled the Wishlist filter parameter
    from_wishlist = request.GET.get('from_wishlist') == 'true'

    # Open Now, Distance, and User Location parameters
    open_now = request.GET.get('open_now') == 'true'
    max_distance = request.GET.get('max_distance')
    user_lat = request.GET.get('user_lat')
    user_lng = request.GET.get('user_lng')

    # Subtask 2: Exclude Low-Rated filter parameter
    exclude_low_rated = request.GET.get('exclude_low_rated') == 'true'

    # Start with all approved restaurants
    restaurants = Restaurant.objects.filter(is_approved=True)

    # Filter by user's wishlist if the checkbox is active and user is logged in
    if from_wishlist and request.user.is_authenticated:
        wishlist_restaurant_ids = Wishlist.objects.filter(user=request.user).values_list('restaurant_id', flat=True)
        restaurants = restaurants.filter(id__in=wishlist_restaurant_ids)

    # Subtask 2: Exclude restaurants where current authenticated user left rating <= 2 stars
    if exclude_low_rated and request.user.is_authenticated:
        low_rated_restaurant_ids = Review.objects.filter(
            author=request.user,
            stars__lte=2
        ).values_list('restaurant_id', flat=True)
        restaurants = restaurants.exclude(id__in=low_rated_restaurant_ids)

    # Apply tag filters (AND logic)
    if selected_cuisine_id and selected_cuisine_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_cuisine_id))
        
    if selected_meal_id and selected_meal_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_meal_id))
        
    # Dietary restriction acts as a hard filter
    if selected_dietary_id and selected_dietary_id.isdigit():
        restaurants = restaurants.filter(tags__id=int(selected_dietary_id))

    # Apply Open-Now filter by matching current server day and time against opening hours
    if open_now:
        now = datetime.now()
        current_day = now.weekday()  # Monday is 0, Sunday is 6
        current_time = now.time()

        restaurants = restaurants.filter(
            hours__day=current_day,
            hours__is_closed=False,
            hours__opening_time__lte=current_time,
            hours__closing_time__gte=current_time
        )

    restaurants = restaurants.distinct()

    # Convert QuerySet to a list for easier manipulation and binding of the distance attribute
    restaurant_list = list(restaurants)

    # Dynamically calculate the physical distance from each restaurant to the user.
    if user_lat and user_lng:
        try:
            u_lat = float(user_lat)
            u_lng = float(user_lng)
            for r in restaurant_list:
                if r.latitude is not None and r.longitude is not None:
                    try:
                        r_lat = float(r.latitude)
                        r_lng = float(r.longitude)
                        # Calculate distance and round to 2 decimal places
                        r.distance = round(calculate_haversine_distance(u_lat, u_lng, r_lat, r_lng), 2)
                    except (ValueError, TypeError):
                        r.distance = None
                else:
                    r.distance = None
        except (ValueError, TypeError):
            pass

    # Filter restaurants outside the max_distance range
    if max_distance and max_distance.isdigit():
        limit_km = float(max_distance)
        restaurant_list = [r for r in restaurant_list if hasattr(r, 'distance') and r.distance is not None and r.distance <= limit_km]

    # Random selection logic
    picked_restaurant = None
    no_matches = False

    # Trigger selection if form is submitted
    if request.GET:
        if len(restaurant_list) > 0:
            picked_restaurant = random.choice(restaurant_list)
        else:
            no_matches = True

    context = {
        'cuisine_tags': cuisine_tags,
        'meal_type_tags': meal_type_tags,
        'dietary_tags': dietary_tags,
        'selected_cuisine_id': int(selected_cuisine_id) if selected_cuisine_id and selected_cuisine_id.isdigit() else None,
        'selected_meal_id': int(selected_meal_id) if selected_meal_id and selected_meal_id.isdigit() else None,
        'selected_dietary_id': int(selected_dietary_id) if selected_dietary_id and selected_dietary_id.isdigit() else None,
        'from_wishlist': from_wishlist,
        'open_now': open_now,
        'max_distance': int(max_distance) if max_distance and max_distance.isdigit() else None,
        'exclude_low_rated': exclude_low_rated,
        'user_lat': user_lat,
        'user_lng': user_lng,
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
    restaurants = Restaurant.objects.filter(is_approved=True).annotate(
        avg_rating=Avg("reviews__stars"),
        review_count=Count("reviews"),
    )
    data = [
        {
            "id": r.id,
            "name": r.name,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "cuisine": r.cuisine,
            "address": r.address,
            "avg_rating": round(r.avg_rating, 1) if r.avg_rating else None,
            "review_count": r.review_count,
        }
        for r in restaurants
    ]
    return JsonResponse(data, safe=False)


def map_view(request):
    return render(request, "restaurants/map.html")


# Feat: Adding a review
@login_required(login_url="login")
def restaurant_detail(request, pk):
    restaurant = get_object_or_404(Restaurant, pk=pk, is_approved=True)
    reviews = restaurant.reviews.all()
    average = reviews.aggregate(Avg("stars"))["stars__avg"]

    user_review = None
    if request.user.is_authenticated:
        user_review = reviews.filter(author=request.user).first()

    if request.method == "POST":
        form = ReviewForm(request.POST, instance=user_review)
        if form.is_valid():
            review = form.save(commit=False)
            review.restaurant = restaurant
            review.author = request.user
            review.save()
            messages.success(request, "Review saved.")
            return redirect("restaurant_detail", pk=restaurant.pk)
    else:
        form = ReviewForm(instance=user_review)

    return render(request, "restaurants/restaurant_detail.html", {
        "restaurant": restaurant,
        "reviews": reviews,
        "average": average,
        "form": form,
        "user_review": user_review,
    })


# Feat: Deleting a review
@login_required(login_url="login")
def delete_review(request, pk):
    review = get_object_or_404(Review, pk=pk, author=request.user)
    restaurant_pk = review.restaurant.pk
    if request.method == "POST":
        review.delete()
        messages.success(request, "Review deleted.")
        return redirect("restaurant_detail", pk=restaurant_pk)
    return render(request, "restaurants/delete_review.html", {"review": review})