from django.views.generic import ListView, DetailView
from .models import CameraModel, Listing


class CameraModelListView(ListView):
    model = CameraModel
    template_name = "market/cameramodel_list.html"
    context_object_name = "models"


class CameraModelDetailView(DetailView):
    model = CameraModel
    template_name = "market/cameramodel_detail.html"
    context_object_name = "camera"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["listings"] = Listing.objects.filter(camera_model=self.object).order_by("-fetched_at")
        return context
