from django.contrib import admin
from .models import Restaurant, Tag, OpeningHour, Review, Wishlist
admin.site.register(OpeningHour)
admin.site.register(Review)
admin.site.register(Wishlist)

class OpeningHourInline(admin.TabularInline):
    # Allow opening hours to be edited directly inside a Restaurant admin page
    model = OpeningHour

    # Show 7 rows by default, one for each day
    extra = 7  # 7 for seven days

@admin.register(Restaurant)
class RestaurantAdmin(admin.ModelAdmin):
    # Display opening hours inside each restaurant's admin page
    inlines = [OpeningHourInline]

    # Columns displayed on the restaurant list page in Django Admin
    list_display = ("name", "cuisine", "added_by", "is_approved")

    # Add sidebar filters
    list_filter = ("is_approved", "cuisine")

    # Allow searching by restaurant name or address
    search_fields = ("name", "address")

    # Add custom bulk approval actions
    actions = ["approve_selected", "unapprove_selected"]

    def approve_selected(self, request, queryset):
        # Mark all selected restaurants as approved
        updated = queryset.update(is_approved=True)

        # Show how many records were updated
        self.message_user(request, f"{updated} restaurants approved.")

    # Text shown in the Django Admin action dropdown
    approve_selected.short_description = "Approve selected restaurants"

    def unapprove_selected(self, request, queryset):
        # Mark all selected restaurants as unapproved
        updated = queryset.update(is_approved=False)

        # Show how many records were updated
        self.message_user(request, f"{updated} restaurants unapproved.")

    # Text shown in the Django Admin action dropdown
    unapprove_selected.short_description = "Unapprove selected restaurants"


# Register Tag using Django's default admin interface
admin.site.register(Tag)