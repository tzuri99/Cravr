from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Restaurant
from .forms import RestaurantForm


def restaurant_list(request):
    restaurants = Restaurant.objects.all()
    return render(request, "restaurants/restaurant_list.html", {"restaurants": restaurants})


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