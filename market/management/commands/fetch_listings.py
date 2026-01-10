from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from market.avito_scraper import fetch_avito_search, extract_avito_id
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

        now = timezone.now()

        # Получаем ВСЕ существующие объявления для этой модели ДО парсинга
        all_existing_before = Listing.objects.filter(
            camera_model=camera_model,
            source=Listing.Source.AVITO
        )
        total_before = all_existing_before.count()
        self.stdout.write(f"Всего объявлений в базе ДО парсинга: {total_before}")

        created = 0
        updated = 0
        found_external_ids = set()
        found_normalized_ids = set()

        for item in items:
            external_id = item.get("external_id")
            if not external_id:
                # Если external_id не передан, пытаемся извлечь из URL
                external_id = extract_avito_id(item.get("url", ""))
                if not external_id:
                    # Если не удалось извлечь, используем последнюю часть URL
                    external_id = item.get("url", "").split("/")[-1].split("?")[0]
            
            obj, was_created = Listing.objects.update_or_create(
                source=Listing.Source.AVITO,
                external_id=external_id,
                defaults={
                    "camera_model": camera_model,
                    "title": item["title"],
                    "url": item["url"],
                    "price": item["price"],
                    "currency": "RUB",
                    "region": item["region"],
                    "is_active": True,
                    "last_seen_at": now,
                },
            )
            found_external_ids.add(external_id)
            # Добавляем нормализованную версию для сравнения
            normalized = extract_avito_id(external_id) if external_id else None
            if normalized:
                found_normalized_ids.add(normalized)
            created += 1 if was_created else 0
            updated += 0 if was_created else 1

        self.stdout.write(f"created={created} updated={updated}")
        self.stdout.write(f"Найдено unique external_id: {len(found_external_ids)}")
        
        # Получаем ВСЕ объявления для этой модели ПОСЛЕ парсинга
        all_existing_after = Listing.objects.filter(
            camera_model=camera_model,
            source=Listing.Source.AVITO
        )
        
        # Находим объявления, которые не были найдены при парсинге
        missing_listings = []
        for listing in all_existing_after:
            old_external_id = listing.external_id
            if not old_external_id:
                # Если external_id пустой, удаляем
                missing_listings.append(listing.id)
                continue
            
            # Нормализуем external_id старой записи
            normalized_old_id = extract_avito_id(old_external_id)
            
            # Проверяем, есть ли это объявление среди найденных
            # Сравниваем по оригинальному external_id и по нормализованному
            is_found = (
                old_external_id in found_external_ids or
                (normalized_old_id and normalized_old_id in found_external_ids) or
                (normalized_old_id and normalized_old_id in found_normalized_ids)
            )
            
            if not is_found:
                missing_listings.append(listing.id)
        
        missing_count = len(missing_listings)
        
        if missing_count > 0:
            # УДАЛЯЕМ объявления, которые не были найдены
            self.stdout.write(f"Найдено объявлений для удаления: {missing_count}")
            deleted_count = Listing.objects.filter(id__in=missing_listings).delete()[0]
            self.stdout.write(f"✓ УДАЛЕНО объявлений (не найдены при парсинге): {deleted_count}")
            
            # Проверяем результат
            total_after = Listing.objects.filter(
                camera_model=camera_model,
                source=Listing.Source.AVITO
            ).count()
            self.stdout.write(f"Осталось объявлений в базе: {total_after} (было {total_before})")
        else:
            self.stdout.write(f"Все объявления актуальны, удалять нечего")
