from django.core.management.base import BaseCommand
from market.models import CameraModel, Listing
from market.avito_scraper import extract_avito_id


class Command(BaseCommand):
    help = 'Удаляет объявления, которые не были найдены при последнем парсинге'

    def add_arguments(self, parser):
        parser.add_argument("--model-id", type=int, default=None, help="ID модели камеры (если не указан, обрабатывает все)")
        parser.add_argument("--dry-run", action="store_true", help="Показать что будет удалено, но не удалять")

    def handle(self, *args, **options):
        model_id = options.get("model_id")
        dry_run = options.get("dry_run", False)

        if model_id:
            models = CameraModel.objects.filter(id=model_id)
        else:
            models = CameraModel.objects.all()

        total_deleted = 0

        for camera in models:
            self.stdout.write(f"\n=== {camera.id} {camera} ===")
            
            # Получаем все активные объявления для этой модели
            active_listings = Listing.objects.filter(
                camera_model=camera,
                source="avito",
                is_active=True
            )
            
            # Получаем все неактивные объявления
            inactive_listings = Listing.objects.filter(
                camera_model=camera,
                source="avito",
                is_active=False
            )
            
            self.stdout.write(f"  Активных: {active_listings.count()}")
            self.stdout.write(f"  Неактивных: {inactive_listings.count()}")
            
            # Собираем external_id активных объявлений (нормализованные)
            active_external_ids = set()
            active_normalized_ids = set()
            
            for listing in active_listings:
                active_external_ids.add(listing.external_id)
                normalized = extract_avito_id(listing.external_id) if listing.external_id else None
                if normalized:
                    active_normalized_ids.add(normalized)
            
            # Находим неактивные объявления, которые не совпадают с активными
            to_delete = []
            for listing in inactive_listings:
                old_external_id = listing.external_id
                normalized_old_id = extract_avito_id(old_external_id) if old_external_id else None
                
                # Проверяем, есть ли это объявление среди активных
                is_found = (
                    old_external_id in active_external_ids or
                    (normalized_old_id and normalized_old_id in active_normalized_ids)
                )
                
                if not is_found:
                    to_delete.append(listing.id)
            
            if to_delete:
                self.stdout.write(f"  Найдено для удаления: {len(to_delete)}")
                
                if dry_run:
                    self.stdout.write(f"  [DRY RUN] Будет удалено: {len(to_delete)} объявлений")
                    for listing_id in to_delete[:5]:  # Показываем первые 5
                        listing = Listing.objects.get(id=listing_id)
                        self.stdout.write(f"    - {listing.external_id}: {listing.title[:50]}")
                    if len(to_delete) > 5:
                        self.stdout.write(f"    ... и еще {len(to_delete) - 5}")
                else:
                    deleted_count = Listing.objects.filter(id__in=to_delete).delete()[0]
                    self.stdout.write(f"  ✓ Удалено: {deleted_count} объявлений")
                    total_deleted += deleted_count
            else:
                self.stdout.write(f"  Нет объявлений для удаления")

        if not dry_run:
            self.stdout.write(f"\nВсего удалено: {total_deleted} объявлений")
        else:
            self.stdout.write(f"\n[DRY RUN] Будет удалено всего: {sum(1 for _ in models)} объявлений")
