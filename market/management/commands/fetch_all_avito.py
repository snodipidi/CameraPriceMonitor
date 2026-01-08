from django.core.management.base import BaseCommand, CommandError
from market.models import CameraModel, Listing
from market.avito_scraper import fetch_avito_search
from django.utils import timezone


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--region", type=str, default="Екатеринбург")
        parser.add_argument("--limit", type=int, default=20)

    def handle(self, *args, **opts):
        models = CameraModel.objects.all().order_by("id")

        for camera in models:
            if not getattr(camera, "avito_search_url", None):
                self.stdout.write(f"skip {camera.id}: no avito_search_url")
                continue

            self.stdout.write(f"=== {camera.id} {camera} ===")

            items = fetch_avito_search(
                camera.avito_search_url,
                region_fallback=opts["region"],
                limit=opts["limit"],
            )

            self.stdout.write(f"avito: parsed items = {len(items)}")

            for item in items:
                Listing.objects.update_or_create(
                    source="avito",
                    external_id=item["url"],
                    defaults={
                        "camera_model": camera,
                        "title": item["title"],
                        "url": item["url"],
                        "price": item["price"],
                        "currency": "RUB",
                        "region": item["region"],
                    },
                )

    now = timezone.now()

    Listing.objects.filter(camera_model=camera, source="avito").update(is_active=False)

    for item in items:
        Listing.objects.update_or_create(
            source="avito",
            external_id=item["url"],
            defaults={
                "camera_model": camera,
                "title": item["title"],
                "url": item["url"],
                "price": item["price"],
                "currency": "RUB",
                "region": item["region"],
                "is_active": True,
                "last_seen_at": now,
            },
        )
