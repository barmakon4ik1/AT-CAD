from django.contrib import admin
from .models import (
    Element,
    GroupElement,
    GroupNumber,
    Period,
    StandardState,
)


# -----------------------------
#  ELEMENT ADMIN
# -----------------------------
@admin.register(Element)
class ElementAdmin(admin.ModelAdmin):
    list_display = (
        'atomic_number',
        'symbol',
        'name_en',
        'name_ru',
        'electron_configuration',
        'period',
        'group_number',
        'standard_state',
    )
    list_filter = (
        'period',
        'group_number',
        'group',
        'standard_state',
        'block',
    )
    search_fields = (
        'symbol',
        'name',
        'name_en',
        'name_ru',
        'name_de',
    )
    ordering = ('atomic_number',)


# -----------------------------
#  GROUP ELEMENT ADMIN
# -----------------------------
@admin.register(GroupElement)
class GroupElementAdmin(admin.ModelAdmin):
    list_display = ('title', 'title_en', 'title_ru', 'title_de')
    search_fields = ('title', 'title_en', 'title_ru', 'title_de')


# -----------------------------
#  GROUP NUMBER ADMIN
# -----------------------------
@admin.register(GroupNumber)
class GroupNumberAdmin(admin.ModelAdmin):
    list_display = ('number',)
    ordering = ('number',)


# -----------------------------
#  PERIOD ADMIN
# -----------------------------
@admin.register(Period)
class PeriodAdmin(admin.ModelAdmin):
    list_display = ('number',)
    ordering = ('number',)


# -----------------------------
#  STANDARD STATE ADMIN
# -----------------------------
@admin.register(StandardState)
class StandardStateAdmin(admin.ModelAdmin):
    list_display = ('key', 'name_en', 'name_ru', 'name_de', 'name_la')
    ordering = ('key',)
    search_fields = ('key', 'name_en', 'name_ru', 'name_de', 'name_la')
