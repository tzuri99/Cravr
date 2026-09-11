from django.contrib import admin
from .models import Restaurant, Tag, OpeningHour, Review

admin.site.register(Review)

class OpeningHourInline(admin.TabularInline):
    model = OpeningHour
    extra = 7  # 7 for seven days

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    inlines = [OpeningHourInline]
    list_display = ("name", "cuisine", "added_by", "is_approved")
    list_filter = ("is_approved", "cuisine")
    search_fields = ("name", "address")
    actions = ["approve_selected", "unapprove_selected"]

    def approve_selected(self, request, queryset):
        updated = queryset.update(is_approved=True)
        self.message_user(request, f"{updated} restaurants approved.")

    approve_selected.short_description = "Approve selected restaurants"

    def unapprove_selected(self, request, queryset):
        updated = queryset.update(is_approved=False)
        self.message_user(request, f"{updated} restaurants unapproved.")

    unapprove_selected.short_description = "Unapprove selected restaurants"

admin.site.register(Tag)