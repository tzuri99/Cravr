from django.urls import path
from . import views

urlpatterns = [
    path("", views.restaurant_list, name="restaurant_list"),
    path("add/", views.add_restaurant, name="add_restaurant"),
]