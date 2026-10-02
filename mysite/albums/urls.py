"""URL configuration for the albums app."""

from django.urls import path

from .views import AlbumDetailView, AlbumKeepsView, AlbumKeepView, AlbumListCreateView

app_name = "albums"

urlpatterns = [
    path("", AlbumListCreateView.as_view(), name="album-list-create"),
    path("<uuid:album_id>/", AlbumDetailView.as_view(), name="album-detail"),
    path("<uuid:album_id>/keeps/", AlbumKeepsView.as_view(), name="album-keeps"),
    path("<uuid:album_id>/keeps/<uuid:keep_id>/", AlbumKeepView.as_view(), name="album-keep"),
]
