from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Min, Max, Count
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView
from django.views.generic import UpdateView

from .forms import WatchItemCreateForm
from .models import CameraModel, Listing, WatchItem


class CameraModelListView(ListView):
    model = CameraModel
    template_name = "market/cameramodel_list.html"
    context_object_name = "models"
    
    def get_queryset(self):
        return CameraModel.objects.select_related('brand').annotate(
            listings_count=Count('listing', distinct=True),
            avg_price=Avg('listing__price'),
            min_price=Min('listing__price'),
            max_price=Max('listing__price'),
        ).order_by('brand__name', 'name')


class CameraModelDetailView(DetailView):
    model = CameraModel
    template_name = "market/cameramodel_detail.html"
    context_object_name = "camera"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        qs = Listing.objects.filter(camera_model=self.object).order_by("-fetched_at")

        context["stats"] = qs.aggregate(
            count=Count("id"),
            avg=Avg("price"),
            min=Min("price"),
            max=Max("price"),
        )

        stats = context["stats"]
        avg_price = stats.get("avg") or 0
        context["good_deal_threshold"] = int(avg_price * 0.9)  # -10%


        paginator = Paginator(qs, 50)
        page_number = self.request.GET.get("page")
        page_obj = paginator.get_page(page_number)

        context["page_obj"] = page_obj
        context["listings"] = page_obj.object_list
        return context


class WatchItemCreateView(LoginRequiredMixin, CreateView):
    model = WatchItem
    form_class = WatchItemCreateForm
    template_name = "market/watchitem_form.html"

    def dispatch(self, request, *args, **kwargs):
        self.camera = get_object_or_404(CameraModel, pk=kwargs["pk"])
        return super().dispatch(request, *args, **kwargs)

    def form_valid(self, form):
        form.instance.user = self.request.user
        form.instance.camera_model = self.camera

        try:
            response = super().form_valid(form)
        except Exception:
            form.add_error(None, "Вы уже отслеживаете эту модель")
            return self.form_invalid(form)

        messages.success(self.request, "Отслеживание сохранено")
        return response

    def get_success_url(self):
        return reverse("watchlist")


class WatchListView(LoginRequiredMixin, ListView):
    model = WatchItem
    template_name = "market/watchlist.html"
    context_object_name = "items"

    def get_queryset(self):
        return (
            WatchItem.objects
            .filter(user=self.request.user)
            .select_related("camera_model", "camera_model__brand")
            .order_by("-created_at")
        )

class WatchItemUpdateView(LoginRequiredMixin, UpdateView):
    model = WatchItem
    form_class = WatchItemCreateForm
    template_name = "market/watchitem_form.html"

    def get_queryset(self):
        return WatchItem.objects.filter(user=self.request.user)

    def get_success_url(self):
        messages.success(self.request, "Отслеживание обновлено")
        return reverse("watchlist")
