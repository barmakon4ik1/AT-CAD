from django.db import models


class StandardOrganization(models.Model):
    """
    ISO, DIN, EN, ASME, ГОСТ и т.д.
    """
    code = models.CharField(max_length=20, unique=True)  # ISO, DIN, EN
    name_en = models.CharField(max_length=200)
    name_ru = models.CharField(max_length=200, blank=True)
    name_de = models.CharField(max_length=200, blank=True)

    class Meta:
        verbose_name = "Организация стандартизации"
        verbose_name_plural = "Организации стандартизации"
        ordering = ["code"]

    def __str__(self):
        return self.code


class StandardSeries(models.Model):
    """
    EN 1092, ASME B16, ISO 7005 и т.п.
    """
    organization = models.ForeignKey(
        StandardOrganization,
        on_delete=models.CASCADE,
        related_name="series"
    )

    code = models.CharField(max_length=50)  # 1092, B16, 7005
    title_en = models.CharField(max_length=300, blank=True)
    title_ru = models.CharField(max_length=300, blank=True)
    title_de = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Серия стандартов"
        verbose_name_plural = "Серии стандартов"
        unique_together = ("organization", "code")
        ordering = ["organization__code", "code"]

    def __str__(self):
        return f"{self.organization.code} {self.code}"


class BaseStandard(models.Model):
    """
    ISO 7005-1, ASME B16.5, EN 1092-1
    """
    series = models.ForeignKey(
        StandardSeries,
        on_delete=models.CASCADE,
        related_name="base_standards"
    )

    number = models.CharField(max_length=50)  # 1, 5, 1-1
    title_en = models.CharField(max_length=500)
    title_ru = models.CharField(max_length=500, blank=True)
    title_de = models.CharField(max_length=500, blank=True)

    class Meta:
        verbose_name = "Базовый стандарт"
        verbose_name_plural = "Базовые стандарты"
        unique_together = ("series", "number")


    def __str__(self):
        return f"{self.series}-{self.number}"


class StandardPart(models.Model):
    """
    Part 1, Type 11, Appendix A и т.п.
    """

    base_standard = models.ForeignKey(
        BaseStandard,
        on_delete=models.CASCADE,
        related_name="parts"
    )

    code = models.CharField(max_length=50)  # Part 1, Type 11, Appendix A

    name_en = models.CharField(max_length=300, blank=True)
    name_ru = models.CharField(max_length=300, blank=True)
    name_de = models.CharField(max_length=300, blank=True)

    class Meta:
        verbose_name = "Часть стандарта"
        verbose_name_plural = "Части стандарта"
        ordering = ["base_standard", "code"]
        unique_together = ("base_standard", "code")

    def __str__(self):
        return f"{self.base_standard} – {self.code}"


class StandardEdition(models.Model):
    base_standard = models.ForeignKey(
        BaseStandard,
        on_delete=models.CASCADE,
        related_name="editions"
    )

    year = models.PositiveSmallIntegerField(null=True, blank=True)
    is_active = models.BooleanField(default=True)

    organizations = models.ManyToManyField(
        StandardOrganization,
        through="StandardEditionOrganization"
    )

    class Meta:
        verbose_name = "Редакция стандарта"
        verbose_name_plural = "Редакции стандартов"
        unique_together = ("base_standard", "year")
        ordering = ["base_standard", "-year"]

    def __str__(self):
        orgs = " ".join(
            o.code for o in self.organizations.all().order_by(
                "standardeditionorganization__position"
            )
        )
        suffix = f":{self.year}" if self.year else ""
        return f"{orgs} {self.base_standard}{suffix}"


class StandardEditionOrganization(models.Model):
    edition = models.ForeignKey(
        StandardEdition,
        on_delete=models.CASCADE,
        related_name="edition_orgs"
    )
    organization = models.ForeignKey(
        StandardOrganization,
        on_delete=models.CASCADE
    )
    position = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ["position"]
        unique_together = ("edition", "organization")

