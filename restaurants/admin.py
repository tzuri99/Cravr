from django.contrib import admin
from .models import Restaurant, Tag, OpeningHour


class OpeningHourInline(admin.TabularInline):
    model = OpeningHour
    extra = 7  # 7 for seven days


@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    inlines = [OpeningHourInline]


admin.site.register(Tag)