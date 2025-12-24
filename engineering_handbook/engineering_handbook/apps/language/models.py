from django.db import models
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType


class Language(models.Model):
    """
    System language (UI / data localization).
    Example: en, ru, de
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO language code, e.g. en, ru, de"
    )

    name = models.CharField(
        max_length=100,
        help_text="Human-readable language name"
    )

    native_name = models.CharField(
        max_length=100,
        blank=True,
        help_text="Language name in its own language"
    )

    is_active = models.BooleanField(default=True)
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        verbose_name = "Язык"
        verbose_name_plural = "Языки"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"


class Translation(models.Model):
    """
    Universal translation for any model and field.
    """

    content_type = models.ForeignKey(
        ContentType,
        on_delete=models.CASCADE,
        verbose_name="Модель"
    )

    object_id = models.PositiveIntegerField(
        verbose_name="ID объекта"
    )

    content_object = GenericForeignKey(
        "content_type",
        "object_id"
    )

    field = models.CharField(
        max_length=50,
        help_text="Translated field name (name, description, title, etc.)"
    )

    language = models.ForeignKey(
        Language,
        on_delete=models.PROTECT,
        related_name="translations"
    )

    text = models.TextField()

    class Meta:
        verbose_name = "Перевод"
        verbose_name_plural = "Переводы"
        unique_together = (
            "content_type",
            "object_id",
            "field",
            "language",
        )
        ordering = ["content_type", "object_id", "field", "language"]

    def __str__(self):
        return f"{self.content_object} [{self.field}] ({self.language.code})"

