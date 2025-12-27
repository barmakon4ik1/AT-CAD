from django.contrib import admin

from .models import (
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
)


# -------------------------
# Базовые справочники
# -------------------------

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


# -------------------------
# Inline: обозначения и аналоги
# -------------------------

class MaterialSymbolicNameInline(admin.TabularInline):
    model = MaterialSymbolicName
    extra = 0


class MaterialEquivalentInline(admin.TabularInline):
    model = MaterialEquivalent
    extra = 0


# -------------------------
# Inline: химический состав
# -------------------------

class MaterialChemicalElementInline(admin.TabularInline):
    model = MaterialChemicalElement
    extra = 0


@admin.register(MaterialChemicalComposition)
class MaterialChemicalCompositionAdmin(admin.ModelAdmin):
    list_display = ("material", "standard")
    list_filter = ("standard",)
    search_fields = ("material__material_number",)
    inlines = (MaterialChemicalElementInline,)


# -------------------------
# Основной материал
# -------------------------

@admin.register(Material)
class MaterialAdmin(admin.ModelAdmin):
    list_display = (
        "material_number",
        "main_group",
        "material_category",
        "iso_15608_group",
        "is_active",
    )
    list_filter = (
        "main_group",
        "material_category",
        "iso_15608_group",
        "is_active",
    )
    search_fields = ("material_number",)
    inlines = (
        MaterialSymbolicNameInline,
        MaterialEquivalentInline,
    )


# -------------------------
# Типы свойств
# -------------------------

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
    search_fields = ("key",)


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
    search_fields = ("key",)


# -------------------------
# Inline: значения свойств
# -------------------------

class MaterialMechanicalPropertyInline(admin.TabularInline):
    model = MaterialMechanicalProperty
    extra = 0


class MaterialPhysicalPropertyInline(admin.TabularInline):
    model = MaterialPhysicalProperty
    extra = 0


# -------------------------
# Наборы свойств
# -------------------------

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
    inlines = (MaterialPhysicalPropertyInline,)
