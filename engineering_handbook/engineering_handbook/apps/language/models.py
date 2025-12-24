from django.db import models


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

    is_active = models.BooleanField(
        default=True,
        help_text="Is language available for selection"
    )

    is_default = models.BooleanField(
        default=False,
        help_text="Default system language"
    )

    sort_order = models.PositiveSmallIntegerField(
        default=0,
        help_text="Ordering in UI"
    )

    class Meta:
        verbose_name = "Язык"
        verbose_name_plural = "Языки"
        ordering = ["sort_order", "code"]

    def __str__(self):
        return f"{self.code} — {self.name}"

