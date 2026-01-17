from django.conf import settings
from django.db import models


# Справочник производителей
class Brand(models.Model):
    # Название бренда
    name = models.CharField(max_length=100, unique=True)
    # Имя для URL
    slug = models.SlugField(max_length=120, unique=True)
    # Как объект будет показываться в админке/списках
    def __str__(self):
        return self.name


# Карточка конкретной модели камеры
class CameraModel(models.Model):
    # Связь “модель камеры принадлежит бренду”.
    brand = models.ForeignKey(
        Brand,
        on_delete=models.CASCADE,
        related_name="camera_models",
    )

    name = models.CharField(max_length=150)

    release_year = models.PositiveSmallIntegerField(null=True, blank=True)
    mount = models.CharField(max_length=50, null=True, blank=True)
    sensor_type = models.CharField(max_length=50, null=True, blank=True)
    avito_search_url = models.URLField(blank=True, default="")
    image_url = models.URLField(blank=True, default="", help_text="Ссылка на изображение камеры")


    def __str__(self):
        return f"{self.brand.name} {self.name}"


# Конкретное объявление с площадки
class Listing(models.Model):
    class Source(models.TextChoices):
        AVITO = "avito", "Avito"

    # Объявление относится к конкретной модели камеры
    camera_model = models.ForeignKey(CameraModel, on_delete=models.CASCADE)


    source = models.CharField(max_length=20, choices=Source.choices)
    external_id = models.CharField(max_length=100)
    title = models.CharField(max_length=255)
    url = models.URLField(max_length=500)
    price = models.IntegerField()
    currency = models.CharField(max_length=10, default="RUB")

    region = models.CharField(max_length=120)
    seller_type = models.CharField(max_length=50, null=True, blank=True)
    posted_date = models.DateField(null=True, blank=True)
    fetched_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    last_seen_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["source", "external_id"],
                name="uniq_listing_source_external_id",
            )
        ]

    def __str__(self):
        return self.title    

# Срез цены во времени
class PriceSnapshot(models.Model):
    listing = models.ForeignKey(
        Listing,
        on_delete=models.CASCADE,
        related_name="price_snapshots",
    )
    price = models.IntegerField()
    currency = models.CharField(max_length=10, default="RUB")

    # Когда именно зафиксировали цену
    checked_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.listing_id} @ {self.price} {self.currency}"


# Отслеживание модели камеры конкретным пользователем
class WatchItem(models.Model):
    # Ссылка на пользователя
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watch_items",
    )
    # Что именно пользователь отслеживает
    camera_model = models.ForeignKey(
        CameraModel,
        on_delete=models.CASCADE,
        related_name="watch_items",
    )
    # Целевая цена
    target_price = models.IntegerField()

    region = models.CharField(max_length=120, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "camera_model"],
                name="uniq_watchitem_user_camera_model",
            )
        ]

    def __str__(self):
        return f"{self.user} → {self.camera_model} (<= {self.target_price})"
