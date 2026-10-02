"""Admin configuration for the albums app."""

from django.contrib import admin

from .models import Album, AlbumKeep


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
