from django.urls import path, include
from .views import (
    CameraModelListView,
    CameraModelDetailView,
    WatchItemCreateView,
    WatchListView,
    WatchItemUpdateView,
    WatchItemDeleteView
)

urlpatterns = [
    path("", CameraModelListView.as_view(), name="camera_list"),
    path("model/<int:pk>/", CameraModelDetailView.as_view(), name="camera_detail"),
    path("watch/add/<int:pk>/", WatchItemCreateView.as_view(), name="watch_add"),
    path("watchlist/", WatchListView.as_view(), name="watchlist"),
    path("accounts/", include("django.contrib.auth.urls")),
    path("watch/edit/<int:pk>/", WatchItemUpdateView.as_view(), name="watch_edit"),
    path("watch/delete/<int:pk>/", WatchItemDeleteView.as_view(), name="watch_delete"),
]
