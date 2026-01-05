from django.urls import path
from . import views

urlpatterns = [
    path("", views.CameraModelListView.as_view(), name="model_list"),
    path("model/<int:pk>/", views.CameraModelDetailView.as_view(), name="model_detail"),
]
