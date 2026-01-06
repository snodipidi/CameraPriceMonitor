from django.urls import path
from .views import (
    CameraModelListView,
    CameraModelDetailView,
    WatchItemCreateView,
    WatchListView,
)

urlpatterns = [
    path("", CameraModelListView.as_view(), name="camera_list"),
    path("model/<int:pk>/", CameraModelDetailView.as_view(), name="camera_detail"),
    path("watch/add/<int:pk>/", WatchItemCreateView.as_view(), name="watch_add"),
    path("watchlist/", WatchListView.as_view(), name="watchlist"),
]
