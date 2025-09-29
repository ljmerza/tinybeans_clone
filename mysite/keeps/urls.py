"""URL configuration for the keeps app."""
from django.urls import path

from .views import (
    KeepListCreateView,
    KeepDetailView,
    KeepByCircleView,
    KeepByTypeView,
    KeepReactionListCreateView,
    KeepReactionDetailView,
    KeepCommentListCreateView,
    KeepCommentDetailView,
    KeepMediaListCreateView,
    KeepMediaDetailView,
    MediaUploadView,
    MediaUploadStatusView,
)

app_name = 'keeps'

urlpatterns = [
    # Keep endpoints
    path('', KeepListCreateView.as_view(), name='keep-list-create'),
    path('<uuid:keep_id>/', KeepDetailView.as_view(), name='keep-detail'),
    path('by-circle/<str:circle_slug>/', KeepByCircleView.as_view(), name='keep-by-circle'),
    path('by-type/', KeepByTypeView.as_view(), name='keep-by-type'),
    
    # Media upload endpoints
    path('upload/', MediaUploadView.as_view(), name='media-upload'),
    path('upload/<uuid:upload_id>/status/', MediaUploadStatusView.as_view(), name='media-upload-status'),
    
    # Reaction endpoints
    path('reactions/', KeepReactionListCreateView.as_view(), name='keep-reaction-list-create'),
    path('reactions/<int:reaction_id>/', KeepReactionDetailView.as_view(), name='keep-reaction-detail'),
    
    # Comment endpoints
    path('comments/', KeepCommentListCreateView.as_view(), name='keep-comment-list-create'),
    path('comments/<int:comment_id>/', KeepCommentDetailView.as_view(), name='keep-comment-detail'),
    
    # Media endpoints
    path('media/', KeepMediaListCreateView.as_view(), name='keep-media-list-create'),
    path('media/<int:media_id>/', KeepMediaDetailView.as_view(), name='keep-media-detail'),
]