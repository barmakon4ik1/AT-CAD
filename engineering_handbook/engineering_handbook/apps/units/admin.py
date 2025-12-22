from django.contrib import admin
from django.forms import BaseInlineFormSet
from django.core.exceptions import ValidationError

from .models import PhysicalQuantity, Unit

# Inline с проверкой «только одна базовая единица»
class UnitInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        base_units = 0
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data.get("DELETE"):
                continue
            if form.cleaned_data.get("is_base"):
                base_units += 1

        if base_units > 1:
            raise ValidationError(
                "Допускается только одна базовая единица для физической величины."
            )

# Inline для Units внутри PhysicalQuantity
class UnitInline(admin.TabularInline):
    model = Unit
    formset = UnitInlineFormSet
    extra = 1

    fields = (
        "key",
        "symbol",
        "name_en",
        "name_ru",
        "name_de",
        "is_base",
        "factor",
        "offset",
    )

    ordering = ("is_base", "key")


# Админка PhysicalQuantity (основная точка ввода)
@admin.register(PhysicalQuantity)
class PhysicalQuantityAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "symbol",
        "name_ru",
        "name_en",
        "name_de",
    )

    search_fields = (
        "key",
        "name_ru",
        "name_en",
        "name_de",
    )

    ordering = ("key",)

    inlines = [UnitInline]


# Отдельная админка Unit (для поиска и контроля)
@admin.register(Unit)
class UnitAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "key",
        "quantity",
        "is_base",
        "factor",
        "offset",
    )

    list_filter = (
        "quantity",
        "is_base",
    )

    search_fields = (
        "symbol",
        "key",
        "name_ru",
        "name_en",
        "name_de",
    )

    ordering = (
        "quantity__key",
        "-is_base",
        "key",
    )

