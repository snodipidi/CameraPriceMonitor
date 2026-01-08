from django.core.management.base import BaseCommand, CommandError

from market.avito_scraper import fetch_avito_search
from market.models import CameraModel, Listing


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--model-id", type=int, required=True)
        parser.add_argument("--source", type=str, required=True)
        parser.add_argument("--region", type=str, default="Россия")
        parser.add_argument("--limit", type=int, default=200)
        parser.add_argument("--search-url", type=str, default=None)

    def handle(self, *args, **options):
        if options["source"] != "avito":
            raise CommandError("Only --source avito is supported right now")

        camera_model = CameraModel.objects.get(pk=options["model_id"])

        search_url = options["search_url"] or camera_model.avito_search_url
        if not search_url:
            raise CommandError(
                f"У CameraModel id={camera_model.id} не задан avito_search_url, "
                f"передайте --search-url или заполните поле в админке."
            )

        items = fetch_avito_search(
            search_url,
            region_fallback=options["region"],
            limit=options["limit"],
        )

        self.stdout.write(f"avito: parsed items = {len(items)}")

        created = 0
        updated = 0

        for item in items:
            obj, was_created = Listing.objects.update_or_create(
                source=Listing.Source.AVITO,
                external_id=item["external_id"],
                defaults={
                    "camera_model": camera_model,
                    "title": item["title"],
                    "url": item["url"],
                    "price": item["price"],
                    "currency": "RUB",
                    "region": item["region"],
                    "is_active": True,
                },
            )
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(f"created={created} updated={updated}")
