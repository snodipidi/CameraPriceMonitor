import pandas as pd
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Avg, Min, Max, Count, Q
from django.shortcuts import get_object_or_404
from django.urls import reverse
from django.views.generic import ListView, DetailView, CreateView
from django.views.generic import UpdateView

from .forms import WatchItemCreateForm
from .models import CameraModel, Listing, WatchItem, PriceSnapshot
from .analytics import (
    calculate_price_statistics,
    create_price_distribution_chart,
    create_price_timeline_chart,
    create_price_by_source_chart,
    create_price_by_condition_chart,
    predict_price_trend,
)


class CameraModelListView(ListView):
    model = CameraModel
    template_name = "market/cameramodel_list.html"
    context_object_name = "models"
    
    def get_queryset(self):
        # Фильтр: только активные объявления с валидной ценой (больше 0)
        active_listings_filter = Q(listing__is_active=True) & Q(listing__price__gt=0)
        queryset = CameraModel.objects.select_related('brand').annotate(
            listings_count=Count('listing', filter=active_listings_filter, distinct=True),
            avg_price=Avg('listing__price', filter=active_listings_filter),
            min_price=Min('listing__price', filter=active_listings_filter),
            max_price=Max('listing__price', filter=active_listings_filter),
        ).order_by('brand__name', 'name')
        
        # Удаляем модели, у которых нет активных объявлений (опционально)
        # queryset = queryset.filter(listings_count__gt=0)
        
        return queryset


class CameraModelDetailView(DetailView):
    model = CameraModel
    template_name = "market/cameramodel_detail.html"
    context_object_name = "camera"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Получаем все активные объявления для модели с валидной ценой (для графиков)
        all_listings_qs = Listing.objects.filter(
            camera_model=self.object, 
            is_active=True,
            price__gt=0
        )
        
        # Получаем отфильтрованные объявления для отображения
        listings_qs = all_listings_qs
        
        # Фильтры из GET параметров
        region_filter = self.request.GET.get('region', '')
        condition_filter = self.request.GET.get('condition', '')
        source_filter = self.request.GET.get('source', '')
        
        if region_filter:
            listings_qs = listings_qs.filter(region__icontains=region_filter)
        if condition_filter:
            listings_qs = listings_qs.filter(condition=condition_filter)
        if source_filter:
            listings_qs = listings_qs.filter(source=source_filter)
        
        # Сортировка из GET параметров
        sort_by = self.request.GET.get('sort', '-fetched_at')
        valid_sorts = {
            'price_asc': 'price',
            'price_desc': '-price',
            'date_asc': 'fetched_at',
            'date_desc': '-fetched_at',
            'date_posted_asc': 'posted_date',
            'date_posted_desc': '-posted_date',
        }
        
        if sort_by in valid_sorts:
            listings_qs = listings_qs.order_by(valid_sorts[sort_by])
        else:
            listings_qs = listings_qs.order_by("-fetched_at")
        
        # Получаем уникальные значения для фильтров
        context['available_regions'] = sorted(set(
            all_listings_qs.values_list('region', flat=True).distinct()
        ))
        context['available_conditions'] = Listing.Condition.choices
        context['available_sources'] = Listing.Source.choices
        
        # Сохраняем текущие значения фильтров
        context['current_region'] = region_filter
        context['current_condition'] = condition_filter
        context['current_source'] = source_filter
        context['current_sort'] = sort_by
        
        # Получаем историю цен из PriceSnapshot
        snapshots_qs = PriceSnapshot.objects.filter(
            listing__camera_model=self.object
        ).select_related('listing').order_by('checked_at')

        # Базовая статистика через ORM (по всем объявлениям для графиков)
        context["stats"] = all_listings_qs.aggregate(
            count=Count("id"),
            avg=Avg("price"),
            min=Min("price"),
            max=Max("price"),
        )

        stats = context["stats"]
        avg_price = stats.get("avg") or 0
        context["good_deal_threshold"] = int(avg_price * 0.9)  # -10%

        # Создаем DataFrame для аналитики (используем все объявления, не отфильтрованные)
        if all_listings_qs.exists():
            listings_data = []
            for listing in all_listings_qs:
                listings_data.append({
                    'id': listing.id,
                    'price': listing.price,
                    'source': listing.source,
                    'condition': listing.condition,
                    'region': listing.region,
                    'fetched_at': listing.fetched_at,
                    'posted_date': listing.posted_date,
                })
            
            df_listings = pd.DataFrame(listings_data)
            
            # Расширенная статистика через Pandas
            extended_stats = calculate_price_statistics(df_listings)
            context["extended_stats"] = extended_stats
            
            # Используем медиану для определения выгодных предложений
            median_price = extended_stats.get('median', avg_price)
            context["good_deal_threshold"] = int(median_price * 0.9)  # -10% от медианы
            
            # Создаем графики
            context["price_distribution_chart"] = create_price_distribution_chart(
                df_listings, 
                f"Распределение цен: {self.object}"
            )
            
            context["price_timeline_chart"] = create_price_timeline_chart(
                df_listings,
                f"Динамика цен: {self.object}"
            )
            
            context["price_by_source_chart"] = create_price_by_source_chart(
                df_listings,
                f"Сравнение цен по источникам: {self.object}"
            )
            
            if 'condition' in df_listings.columns and df_listings['condition'].notna().any():
                context["price_by_condition_chart"] = create_price_by_condition_chart(
                    df_listings,
                    f"Цены по состоянию: {self.object}"
                )
            
            # Прогнозирование тренда
            if len(df_listings) >= 3:
                # Для прогноза используем историю цен из PriceSnapshot, если есть
                if snapshots_qs.exists():
                    snapshots_data = []
                    for snapshot in snapshots_qs:
                        snapshots_data.append({
                            'price': snapshot.price,
                            'checked_at': snapshot.checked_at,
                        })
                    df_snapshots = pd.DataFrame(snapshots_data)
                    context["price_prediction"] = predict_price_trend(df_snapshots)
                else:
                    # Если нет истории, используем объявления
                    context["price_prediction"] = predict_price_trend(df_listings)
        else:
            context["extended_stats"] = calculate_price_statistics(pd.DataFrame())
            context["price_distribution_chart"] = ""
            context["price_timeline_chart"] = ""
            context["price_by_source_chart"] = ""
            context["price_by_condition_chart"] = ""
            context["price_prediction"] = None

        # Статистика по отфильтрованным объявлениям (для отображения)
        filtered_stats = listings_qs.aggregate(
            count=Count("id"),
        )
        context["filtered_count"] = filtered_stats.get("count", 0)
        
        # Пагинация для списка объявлений
        paginator = Paginator(listings_qs, 50)
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
