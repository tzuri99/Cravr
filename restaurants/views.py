import math
import random
from datetime import datetime
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from .forms import OpeningHourFormSet, RestaurantForm, ReviewForm
from .models import Restaurant, Review, ReviewPhoto, Tag, Wishlist
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


# Require the user to be logged in before submitting a restaurant
@login_required
def add_restaurant(request):
    # Handle submitted restaurant and opening-hour data
    if request.method == "POST":
        form = RestaurantForm(request.POST)
        formset = OpeningHourFormSet(request.POST)

        # Continue only if both the restaurant form and opening-hour formset are valid
        if form.is_valid() and formset.is_valid():
            # Create the Restaurant object without saving yet so extra fields can be assigned
            restaurant = form.save(commit=False)
            # Record the user who submitted the restaurant
            restaurant.added_by = request.user
            # New user-submitted restaurants require admin approval
            restaurant.is_approved = False
            # Save the restaurant before linking opening hours to it
            restaurant.save()
            # Link the opening-hour formset to this restaurant
            formset.instance = restaurant
            formset.save()
            # Automatically assign relevant tags to the restaurant
            apply_intelligent_tags(restaurant)
            # Show a confirmation message after submission
            messages.success(request, "Restaurant submitted. It will be visible once approved.")
            # Return to the restaurant list page
            return redirect("restaurant_list")
    else:
        # Show an empty restaurant form for a normal GET request
        form = RestaurantForm()

        # Pre-create one opening-hour row for each day of the week
        formset = OpeningHourFormSet(initial=[{"day": day} for day in range(7)])

    # Render the restaurant submission page
    return render(request, "restaurants/add_restaurant.html", {"form": form, "formset": formset})

def restaurant_picker(request):
    # Branch feature: Random restaurant selection logic
    cuisine_tags = Tag.objects.filter(tag_type__iexact='cuisine')
    meal_type_tags = Tag.objects.filter(tag_type__iexact='meal_type')
    dietary_tags = Tag.objects.filter(tag_type__iexact='dietary')

    selected_cuisine_id = request.GET.get('cuisine')
    selected_meal_id = request.GET.get('meal_type')
    selected_dietary_id = request.GET.get('dietary')

    # Filter option for user's own reviews: 'reviewed', 'not_reviewed', or 'all'
    review_filter = request.GET.get('review_filter', 'all')

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

    # Filter based on whether the authenticated user has reviewed the restaurant
    if request.user.is_authenticated:
        user_reviewed_ids = Review.objects.filter(author=request.user).values_list('restaurant_id', flat=True)
        
        if review_filter == 'reviewed':
            # Include only restaurants reviewed by the current user
            restaurants = restaurants.filter(id__in=user_reviewed_ids)
        elif review_filter == 'not_reviewed':
            # Exclude restaurants reviewed by the current user
            restaurants = restaurants.exclude(id__in=user_reviewed_ids)

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
        'review_filter': review_filter,
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
    """Add or remove restaurant from user's wishlist seamlessly via AJAX or standard GET/POST request."""
    restaurant = get_object_or_404(Restaurant, id=restaurant_id)
    wishlist_item = Wishlist.objects.filter(user=request.user, restaurant=restaurant).first()

    if wishlist_item:
        wishlist_item.delete()
        is_in_wishlist = False
        message_text = f"Removed {restaurant.name} from your wishlist."
    else:
        Wishlist.objects.get_or_create(user=request.user, restaurant=restaurant)
        is_in_wishlist = True
        message_text = f"Added {restaurant.name} to your wishlist!"

    # Check if request was sent asynchronously (AJAX / Fetch API)
    is_ajax = (
        request.headers.get('x-requested-with') == 'XMLHttpRequest' or
        request.content_type == 'application/json' or
        request.META.get('HTTP_X_REQUESTED_WITH') == 'XMLHttpRequest'
    )

    if is_ajax:
        return JsonResponse({
            'status': 'success',
            'is_in_wishlist': is_in_wishlist,
            'restaurant_id': restaurant_id,
            'message': message_text
        })

    # Standard non-AJAX fallback redirection
    if is_in_wishlist:
        messages.success(request, message_text)
    else:
        messages.info(request, message_text)

    return redirect(request.META.get('HTTP_REFERER', 'restaurant_list'))


@login_required
def wishlist_list(request):
    """Display user's wishlisted restaurants."""
    wishlist_items = Wishlist.objects.filter(user=request.user).select_related('restaurant')
    return render(request, 'restaurants/wishlist.html', {'wishlist_items': wishlist_items})


def restaurants_json(request):
    # Only approved restaurants should appear on the map
    restaurants = Restaurant.objects.filter(is_approved=True)

    # Read the current visible map boundaries from the query string
    south = request.GET.get("south")
    west = request.GET.get("west")
    north = request.GET.get("north")
    east = request.GET.get("east")

    # Filter restaurants to the currently visible map area if all bounds are provided
    if all([south, west, north, east]):
        try:
            restaurants = restaurants.filter(
                latitude__gte=float(south),
                latitude__lte=float(north),
                longitude__gte=float(west),
                longitude__lte=float(east),
            )
        # Ignore invalid coordinate values instead of causing the request to fail
        except ValueError:
            pass

    # Add calculated review information to each restaurant and limit the response size for map performance
    restaurants = restaurants.annotate(
        avg_rating=Avg("reviews__stars"),
        review_count=Count("reviews"),
    )[:1500]

    # Convert restaurant objects into JSON-friendly dictionaries
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

    # safe=False allows JsonResponse to return a list directly
    return JsonResponse(data, safe=False)


def map_view(request):
    # Render the page containing the interactive restaurant map
    return render(request, "restaurants/map.html")


# Feat: Adding a review
@login_required(login_url="login")
def restaurant_detail(request, pk):
    # Retrieve the approved restaurant or return a 404 if it does not exist
    restaurant = get_object_or_404(Restaurant, pk=pk, is_approved=True)

    # Get all reviews belonging to this restaurant
    reviews = restaurant.reviews.all()

    # Calculate the restaurant's average star rating
    average = reviews.aggregate(Avg("stars"))["stars__avg"]

    # Handle review submission
    if request.method == "POST":
        form = ReviewForm(request.POST)

        # Save the review only when the submitted form is valid
        if form.is_valid():
            # Create the review without saving so restaurant and author can be assigned first
            review = form.save(commit=False)
            review.restaurant = restaurant
            review.author = request.user
            review.save()

            # Get up to 5 uploaded review photos
            photos = request.FILES.getlist("photos")[:5]

            # Save each uploaded photo as a separate ReviewPhoto record
            for photo in photos:
                ReviewPhoto.objects.create(review=review, image=photo)

            # Show confirmation after the review is created
            messages.success(request, "Review posted.")

            # Reload the restaurant detail page
            return redirect("restaurant_detail", pk=restaurant.pk)
    else:
        # Display an empty review form for normal page loads
        form = ReviewForm()

    # Pass restaurant, review, rating, and form data to the template
    return render(request, "restaurants/restaurant_detail.html", {
        "restaurant": restaurant,
        "reviews": reviews,
        "average": average,
        "form": form,
    })


# Feat: Deleting a review
@login_required(login_url="login")
def delete_review(request, pk):
    # Only allow the original author to delete the review
    review = get_object_or_404(Review, pk=pk, author=request.user)

    # Store the restaurant ID before the review is deleted
    restaurant_pk = review.restaurant.pk

    # Delete only after the confirmation form is submitted
    if request.method == "POST":
        review.delete()

        # Show a success message after deletion
        messages.success(request, "Review deleted.")

        # Return to the restaurant detail page
        return redirect("restaurant_detail", pk=restaurant_pk)

    # Show the delete confirmation page first
    return render(request, "restaurants/delete_review.html", {"review": review})


# Feat: Editing a review
@login_required(login_url="login")
def edit_review(request, pk):
    # Only allow the original author to edit the review
    review = get_object_or_404(
        Review,
        pk=pk,
        author=request.user
    )

    # Handle submitted review edits
    if request.method == "POST":
        form = ReviewForm(
            request.POST,
            request.FILES,
            instance=review
        )

        if form.is_valid():
            # Save updated rating and review text
            form.save()

            # Get IDs of existing photos selected for deletion
            delete_photo_ids = request.POST.getlist("delete_photos")

            # Only retrieve selected photos belonging to this review
            photos_to_delete = review.photos.filter(
                id__in=delete_photo_ids
            )

            # Delete both the stored image file and its database record
            for photo in photos_to_delete:
                if photo.image:
                    photo.image.delete(save=False)

                photo.delete()

            # Count how many photos remain after deletion
            existing_count = review.photos.count()

            # Calculate how many additional photos can still be added
            available_slots = max(
                0,
                5 - existing_count
            )

            # Get newly uploaded photos
            new_photos = request.FILES.getlist(
                "photos"
            )

            # Save only enough photos to keep the total at 5 or fewer
            for photo in new_photos[:available_slots]:
                ReviewPhoto.objects.create(
                    review=review,
                    image=photo
                )

            # Show confirmation after saving the updated review
            messages.success(
                request,
                "Review updated."
            )

            # Return to the related restaurant detail page
            return redirect(
                "restaurant_detail",
                pk=review.restaurant.pk
            )

    else:
        # Pre-fill the form with the review's existing values
        form = ReviewForm(
            instance=review
        )

    # Display the review editing page
    return render(
        request,
        "restaurants/edit_review.html",
        {
            "form": form,
            "review": review
        }
    )