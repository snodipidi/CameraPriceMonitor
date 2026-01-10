from django.core.management.base import BaseCommand, CommandError
from market.models import CameraModel, Listing
from market.avito_scraper import fetch_avito_search, extract_avito_id
from django.utils import timezone


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument("--region", type=str, default="Екатеринбург")
        parser.add_argument("--limit", type=int, default=20)
        parser.add_argument("--keep-missing", action="store_true", help="Не удалять объявления, которые не были найдены (только деактивировать)")

    def handle(self, *args, **opts):
        models = CameraModel.objects.all().order_by("id")
        keep_missing = opts.get("keep_missing", False)

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

            now = timezone.now()
            
            # Собираем external_id всех найденных объявлений (и нормализованные версии)
            found_external_ids = set()
            found_normalized_ids = set()
            
            # Обновляем или создаем найденные объявления
            created = 0
            updated = 0
            
            for item in items:
                # Используем external_id из результата парсинга
                external_id = item.get("external_id")
                if not external_id:
                    # Если external_id не передан, пытаемся извлечь из URL
                    external_id = extract_avito_id(item.get("url", ""))
                    if not external_id:
                        # Если не удалось извлечь, используем последнюю часть URL
                        external_id = item.get("url", "").split("/")[-1].split("?")[0]
                
                obj, was_created = Listing.objects.update_or_create(
                    source="avito",
                    external_id=external_id,
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
                found_external_ids.add(external_id)
                # Добавляем нормализованную версию для сравнения
                normalized = extract_avito_id(external_id) if external_id else None
                if normalized:
                    found_normalized_ids.add(normalized)
                created += 1 if was_created else 0
                updated += 0 if was_created else 1

            self.stdout.write(f"  Создано: {created}, Обновлено: {updated}")
            self.stdout.write(f"  Найдено external_id: {len(found_external_ids)}")
            
            # Получаем ВСЕ объявления для этой модели из Avito
            all_listings = Listing.objects.filter(
                camera_model=camera,
                source="avito"
            )
            
            total_before = all_listings.count()
            self.stdout.write(f"  Всего объявлений в базе для модели: {total_before}")
            
            # Находим объявления, которые не были найдены при парсинге
            # Удаляем те, которых нет в списке найденных
            missing_listings = []
            for listing in all_listings:
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
                if keep_missing:
                    # Только деактивируем, не удаляем
                    Listing.objects.filter(id__in=missing_listings).update(is_active=False)
                    self.stdout.write(f"  Деактивировано объявлений (не найдены при парсинге): {missing_count}")
                else:
                    # УДАЛЯЕМ объявления, которые не были найдены
                    deleted_count = Listing.objects.filter(id__in=missing_listings).delete()[0]
                    self.stdout.write(f"  ✓ УДАЛЕНО объявлений (не найдены при парсинге): {deleted_count}")
                    
                    # Проверяем результат
                    total_after = Listing.objects.filter(
                        camera_model=camera,
                        source="avito"
                    ).count()
                    self.stdout.write(f"  Осталось объявлений в базе: {total_after} (было {total_before})")
            else:
                self.stdout.write(f"  Все объявления актуальны, удалять нечего")
