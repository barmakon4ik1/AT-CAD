from django.contrib import admin

from .models import (
    StandardOrganization,
    StandardSeries,
    BaseStandard,
    StandardEdition,
    StandardEditionOrganization,
    StandardPart,
)


# ============================================================
# Организации стандартизации (ISO, DIN, EN, ASME, ГОСТ и т.д.)
# ============================================================

@admin.register(StandardOrganization)
class StandardOrganizationAdmin(admin.ModelAdmin):
    list_display = ("code", "name_en", "name_ru", "name_de")
    search_fields = ("code", "name_en", "name_ru", "name_de")
    ordering = ("code",)


# ============================================================
# Серии стандартов (EN 1092, ASME B16, ISO 7005 и т.п.)
# ============================================================

@admin.register(StandardSeries)
class StandardSeriesAdmin(admin.ModelAdmin):
    list_display = ("organization", "code", "title_en")
    list_filter = ("organization",)
    search_fields = ("code", "title_en", "title_ru", "title_de")
    ordering = ("organization__code", "code")


# ============================================================
# Inline: части стандарта (Part 1, Type 11, Appendix A ...)
# ============================================================

class StandardPartInline(admin.TabularInline):
    model = StandardPart
    extra = 1
    fields = ("code", "name_en", "name_ru", "name_de")
    ordering = ("code",)
    show_change_link = True


# ============================================================
# Inline: издания стандарта (внутри BaseStandard)
# ============================================================

class StandardEditionInline(admin.TabularInline):
    model = StandardEdition
    extra = 0
    fields = ("year", "is_active")
    show_change_link = True


# ============================================================
# Inline: организации в издании (DIN EN ISO ...)
# ============================================================

class StandardEditionOrganizationInline(admin.TabularInline):
    model = StandardEditionOrganization
    extra = 1
    ordering = ("position",)
    autocomplete_fields = ("organization",)


# ============================================================
# Базовый стандарт (ISO 7005-1, EN 1092-1, ASME B16.5 ...)
# ============================================================

@admin.register(BaseStandard)
class BaseStandardAdmin(admin.ModelAdmin):
    list_display = ("__str__", "separator", "title_en")
    search_fields = (
        "series__organization__code",
        "series__code",
        "number",
        "title_en",
        "title_ru",
        "title_de",
    )
    list_filter = ("series__organization",)
    ordering = ("series__organization__code", "series__code", "number")

    inlines = [StandardPartInline, StandardEditionInline]



# ============================================================
# Издание стандарта (DIN EN ISO 12345:2020 и т.п.)
# ============================================================

@admin.register(StandardEdition)
class StandardEditionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "base_standard", "year", "is_active")
    list_filter = ("is_active", "year", "base_standard__series__organization")
    search_fields = (
        "base_standard__number",
        "base_standard__series__code",
    )
    ordering = ("base_standard", "-year")

    inlines = [StandardEditionOrganizationInline]

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.prefetch_related(
            "organizations",
            "edition_orgs__organization",
        )
