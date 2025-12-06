from django.contrib import admin
from .models import Element

@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = ('atomic_number', 'symbol', 'name_en', 'name_ru', 'category')
    list_filter = ('category', 'period')
    search_fields = ('symbol', 'name_en', 'name_ru', 'name_de')
    ordering = ('atomic_number',)