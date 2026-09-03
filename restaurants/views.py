from django.contrib import messages
from django.shortcuts import render, redirect
from .models import Restaurant
from .forms import RestaurantForm
from .forms import RestaurantForm, OpeningHourFormSet

def restaurant_list(request):
    restaurants = Restaurant.objects.all()
    return render(request, "restaurants/restaurant_list.html", {"restaurants": restaurants})

def add_restaurant(request):
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