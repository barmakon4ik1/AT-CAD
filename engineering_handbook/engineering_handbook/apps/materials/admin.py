from django.contrib import admin
from .models import (
    StandardSystem,
    MaterialCategory,
    ISO15608Group,
    Material,
    MaterialSymbolicName,
    MaterialEquivalent,
    MaterialChemicalComposition,
    MaterialChemicalElement,
    MechanicalPropertyType,
    PhysicalPropertyType,
    MaterialMechanicalPropertySet,
    MaterialMechanicalProperty,
    MaterialPhysicalPropertySet,
    MaterialPhysicalProperty,
    MaterialAnalogue,
)

# ============================================================
# Базовые справочники
# ============================================================

@admin.register(StandardSystem)
class StandardSystemAdmin(admin.ModelAdmin):
    list_display = ("key", "name", "is_primary", "sort_order")
    list_editable = ("is_primary", "sort_order")
    ordering = ("sort_order", "key")
    search_fields = ("key", "name")


@admin.register(MaterialCategory)
class MaterialCategoryAdmin(admin.ModelAdmin):
    list_display = ("key", "sort_order", "is_active")
    ordering = ("sort_order", "key")
    list_editable = ("sort_order", "is_active")
    search_fields = ("key",)


@admin.register(ISO15608Group)
class ISO15608GroupAdmin(admin.ModelAdmin):
    list_display = ("code", "is_active")
    list_editable = ("is_active",)
    search_fields = ("code",)


# ============================================================
# Inline: Обозначения и аналоги
# ============================================================

class MaterialSymbolicNameInline(admin.TabularInline):
    model = MaterialSymbolicName
    extra = 0
    show_change_link = True


class MaterialEquivalentInline(admin.TabularInline):
    model = MaterialEquivalent
    extra = 0
    show_change_link = True


# ============================================================
# Inline: Химический состав
# ============================================================

class MaterialChemicalElementInline(admin.TabularInline):
    model = MaterialChemicalElement
    extra = 0
    autocomplete_fields = ("element",)


@admin.register(MaterialChemicalComposition)
class MaterialChemicalCompositionAdmin(admin.ModelAdmin):
    list_display = ("material", "standard")
    list_filter = ("standard",)
    search_fields = ("material__material_number",)
    autocomplete_fields = ("material", "standard")
    inlines = (MaterialChemicalElementInline,)


# ============================================================
# Основной материал
# ============================================================

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "material_number",
        "standard_system",
        "main_group",
        "material_category",
        "iso_15608_group",
        "is_active",
    )
    list_filter = (
        "standard_system",
        "main_group",
        "material_category",
        "iso_15608_group",
        "is_active",
    )
    search_fields = ("material_number",)
    autocomplete_fields = (
        "standard_system",
        "material_category",
        "iso_15608_group",
    )

    inlines = (
        MaterialSymbolicNameInline,
        MaterialEquivalentInline,
    )

    fieldsets = (
        ("Идентификация", {
            "fields": (
                "material_number",
                "standard_system",
                "main_group",
                "material_category",
                "iso_15608_group",
            )
        }),
        ("Статус", {
            "fields": ("is_active",)
        }),
    )


# ============================================================
# Типы свойств
# ============================================================

@admin.register(MechanicalPropertyType)
class MechanicalPropertyTypeAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "symbol",
        "physical_quantity",
        "default_unit",
        "sort_order",
        "is_active",
    )
    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "key")
    search_fields = ("key", "symbol")


@admin.register(PhysicalPropertyType)
class PhysicalPropertyTypeAdmin(admin.ModelAdmin):
    list_display = (
        "key",
        "symbol",
        "physical_quantity",
        "default_unit",
        "sort_order",
        "is_active",
    )
    list_editable = ("sort_order", "is_active")
    ordering = ("sort_order", "key")
    search_fields = ("key", "symbol")


# ============================================================
# Inline: Значения свойств
# ============================================================

class MaterialMechanicalPropertyInline(admin.TabularInline):
    model = MaterialMechanicalProperty
    extra = 0
    autocomplete_fields = ("property_type",)


class MaterialPhysicalPropertyInline(admin.TabularInline):
    model = MaterialPhysicalProperty
    extra = 0
    autocomplete_fields = ("property_type",)


# ============================================================
# Наборы свойств
# ============================================================

@admin.register(MaterialMechanicalPropertySet)
class MaterialMechanicalPropertySetAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "standard_edition",
        "temperature_min",
        "temperature_max",
    )
    list_filter = ("standard_edition",)
    search_fields = ("material__material_number",)
    autocomplete_fields = ("material", "standard_edition")
    inlines = (MaterialMechanicalPropertyInline,)


@admin.register(MaterialPhysicalPropertySet)
class MaterialPhysicalPropertySetAdmin(admin.ModelAdmin):
    list_display = (
        "material",
        "standard_edition",
        "temperature_min",
        "temperature_max",
    )
    list_filter = ("standard_edition",)
    search_fields = ("material__material_number",)
    autocomplete_fields = ("material", "standard_edition")
    inlines = (MaterialPhysicalPropertyInline,)


# ============================================================
# Кросс-системные аналоги
# ============================================================

@admin.register(MaterialAnalogue)
class MaterialAnalogueAdmin(admin.ModelAdmin):
    list_display = ("from_system", "from_material_code", "to_system", "to_material_code", "equivalence_type")
    list_filter = ("from_system", "to_system", "equivalence_type")
    search_fields = ("from_material_code", "to_material_code", "notes")
