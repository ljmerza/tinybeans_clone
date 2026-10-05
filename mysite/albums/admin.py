"""Admin configuration for the albums app."""

from django.contrib import admin

from .models import Album, AlbumKeep, MonthlyRecap


class AlbumKeepInline(admin.TabularInline):
    model = AlbumKeep
    extra = 0
    raw_id_fields = ["keep", "added_by"]
    readonly_fields = ["added_at"]


@admin.register(Album)
class AlbumAdmin(admin.ModelAdmin):
    list_display = ["name", "circle", "created_by", "created_at", "updated_at"]
    list_filter = ["circle"]
    search_fields = ["name", "description"]
    raw_id_fields = ["created_by", "cover_keep"]
    inlines = [AlbumKeepInline]


@admin.register(MonthlyRecap)
class MonthlyRecapAdmin(admin.ModelAdmin):
    """Deleting a row lets ``create_monthly_recap`` make that month again."""

    list_display = ["month", "circle", "album", "created_at"]
    list_filter = ["circle"]
    raw_id_fields = ["album"]
