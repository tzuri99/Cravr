from django.urls import path
from . import views

urlpatterns = [
    path("", views.restaurant_list, name="restaurant_list"),
    path("add/", views.add_restaurant, name="add_restaurant"),
    path('picker/', views.restaurant_picker, name='restaurant_picker'),
    path("map/", views.map_view, name="map_view"),
    path("api/restaurants/", views.restaurants_json, name="restaurants_json"),
]