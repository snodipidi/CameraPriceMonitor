from django.views.generic import ListView, DetailView
from .models import CameraModel, Listing
from django.db.models import Avg, Min, Max, Count



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

        qs = Listing.objects.filter(camera_model=self.object)

        context["listings"] = qs.order_by("-fetched_at")
        context["stats"] = qs.aggregate(
            count=Count("id"),
            avg=Avg("price"),
            min=Min("price"),
            max=Max("price"),
        )
        return context
