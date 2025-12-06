# engineering_handbook/apps/elements/management/commands/import_elements.py

import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.conf import settings

# Устанавливаем корректный импорт моделей через Django
import django
django.setup()

from engineering_handbook.apps.elements.models import Element


class Command(BaseCommand):
    help = "Импорт элементов из JSON файла"

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            help='Путь к JSON файлу с элементами',
            required=True
        )
        parser.add_argument(
            '--flush',
            action='store_true',
            help='Очистить таблицу элементов перед импортом',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        if not file_path.exists():
            self.stderr.write(f"Файл {file_path} не найден")
            return

        if options['flush']:
            Element.objects.all().delete()
            self.stdout.write("Таблица элементов очищена")

        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)

        for elem_data in data:
            # пример: предполагаем, что JSON содержит 'name', 'symbol', 'atomic_number'
            Element.objects.create(
                name=elem_data['name_en'],
                symbol=elem_data['symbol'],
                atomic_number=elem_data['atomic_number']
            )

        self.stdout.write(self.style.SUCCESS(f"Импортировано {len(data)} элементов"))
