"""Admin configuration for the albums app."""

from django.contrib import admin

from .models import Album, AlbumKeep, BirthdayAlbum, MilestoneAlbum, MilestoneSuggestion, MonthlyRecap


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


@admin.register(BirthdayAlbum)
class BirthdayAlbumAdmin(admin.ModelAdmin):
    """Deleting a row (or its album) turns the circle's birthdays album off."""

    list_display = ["circle", "album", "created_at"]
    raw_id_fields = ["album"]


@admin.register(MilestoneAlbum)
class MilestoneAlbumAdmin(admin.ModelAdmin):
    """Fix which album is a circle's Milestones album; with no row, the next approval makes one."""

    list_display = ["circle", "album", "created_at"]
    raw_id_fields = ["album"]


@admin.register(MilestoneSuggestion)
class MilestoneSuggestionAdmin(admin.ModelAdmin):
    """Deleting a row lets the post be suggested again."""

    list_display = ["keep", "circle", "status", "source", "label", "created_at", "decided_by", "decided_at"]
    list_filter = ["status", "source", "circle"]
    search_fields = ["label", "source_token_prefix"]
    raw_id_fields = ["keep", "decided_by"]
    readonly_fields = ["created_at"]
