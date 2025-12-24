from django.contrib import admin
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.admin import GenericTabularInline
from django.utils.text import Truncator
from .models import Language, Translation


@admin.register(Language)
class LanguageAdmin(admin.ModelAdmin):
    list_display = (
        "code",
        "name",
        "native_name",
        "is_active",
        "is_default",
        "sort_order",
    )
    list_editable = ("is_active", "is_default", "sort_order")
    ordering = ("sort_order", "code")
    search_fields = ("code", "name", "native_name")

class TranslationInline(GenericTabularInline):
    model = Translation
    extra = 1

    fields = ("field", "language", "text")
    autocomplete_fields = ("language",)

    verbose_name = "Перевод"
    verbose_name_plural = "Переводы"


@admin.register(ContentType)
class ContentTypeAdmin(admin.ModelAdmin):
    search_fields = ("app_label", "model")


@admin.register(Translation)
class TranslationAdmin(admin.ModelAdmin):
    list_display = (
        "content_type",
        "object_id",
        "field",
        "language",
        "short_text",
    )
    list_filter = ("language", "content_type", "field")
    search_fields = ("text",)
    ordering = ("content_type", "object_id", "field", "language")
    autocomplete_fields = ("content_type",)

    def short_text(self, obj):
        return Truncator(obj.text).chars(50)

    short_text.short_description = "Текст"
