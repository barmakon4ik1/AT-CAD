from django.db import models


class MaterialCategory(models.Model):
    """
    Metallurgical category
    (Austenitic, Duplex, Ferritic, etc.)
    """

    key = models.CharField(
        max_length=50,
        unique=True,
        help_text="Stable key, e.g. austenitic, duplex"
    )

    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Категория материала"
        verbose_name_plural = "Категории материалов"
        ordering = ("sort_order", "key")

    def __str__(self):
        return self.key


class ISO15608Group(models.Model):
    """
    Material group according to ISO/TR 15608
    (e.g. 8.1, 8.2, 10)
    """

    code = models.CharField(
        max_length=10,
        unique=True,
        help_text="ISO/TR 15608 group code"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Группа материала ISO/TR 15608"
        verbose_name_plural = "Группы материалов ISO/TR 15608"
        ordering = ("code",)

    def __str__(self):
        return self.code


class Material(models.Model):
    """
    Base material according to DIN EN 10027-2
    """

    material_number = models.CharField(
        max_length=10,
        unique=True,
        help_text="DIN EN 10027-2 number, e.g. 1.4571"
    )

    main_group = models.PositiveSmallIntegerField(
        help_text="1 = Steel, 2 = Heavy metals, 3 = Light metals"
    )

    steel_group_en10020 = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="40–49 according to DIN EN 10020 (only for steels)"
    )

    material_category = models.ForeignKey(
        MaterialCategory,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials"
    )

    iso_15608_group = models.ForeignKey(
        ISO15608Group,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="materials"
    )

    is_active = models.BooleanField(default=True)

    class Meta:
        verbose_name = "Материал"
        verbose_name_plural = "Материалы"
        ordering = ("material_number",)

    def __str__(self):
        return self.material_number


class MaterialSymbolicName(models.Model):
    """
    Symbolic designation according to a specific standard
    (e.g. X6CrNiMoTi17-12-2)
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="symbolic_names"
    )

    symbol = models.CharField(
        max_length=100,
        help_text="e.g. X6CrNiMoTi17-12-2"
    )

    standard = models.ForeignKey(
        "standards.StandardEdition",
        on_delete=models.PROTECT,
        related_name="symbolic_materials"
    )

    is_preferred = models.BooleanField(default=False)

    class Meta:
        unique_together = ("material", "symbol")

    def __str__(self):
        return self.symbol


class MaterialEquivalent(models.Model):
    """
    Equivalent or comparable material designation
    according to another standard system
    (e.g. AISI 316L, UNS S31635)
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="equivalents"
    )

    standard = models.ForeignKey(
        "standards.StandardEdition",
        on_delete=models.PROTECT,
        related_name="material_equivalents"
    )

    designation = models.CharField(
        max_length=100,
        help_text="e.g. AISI 316L"
    )

    equivalence_type = models.CharField(
        max_length=20,
        choices=[
            ("equivalent", "Equivalent"),
            ("approximate", "Approximate"),
            ("comparable", "Comparable"),
        ],
        default="equivalent"
    )

    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ("material", "standard", "designation")

    def __str__(self):
        return self.designation


class MaterialChemicalComposition(models.Model):
    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="chemical_compositions"
    )

    standard = models.ForeignKey(
        "standards.StandardEdition",
        on_delete=models.PROTECT,
        help_text="Standard defining chemical composition"
    )

    class Meta:
        unique_together = ("material", "standard")
        verbose_name = "Химический состав материала"
        verbose_name_plural = "Химические составы материалов"

    def __str__(self):
        return f"{self.material} – {self.standard}"


class MaterialChemicalElement(models.Model):
    composition = models.ForeignKey(
        MaterialChemicalComposition,
        on_delete=models.CASCADE,
        related_name="elements"
    )

    element = models.ForeignKey(
        "elements.ChemicalElement",
        on_delete=models.PROTECT
    )

    unit = models.ForeignKey(
        "units.Unit",
        on_delete=models.PROTECT,
        limit_choices_to={"key": "percent"}
    )

    min_value = models.FloatField(default=0.0)
    max_value = models.FloatField()

    class Meta:
        unique_together = ("composition", "element")
        verbose_name = "Химический элемент"
        verbose_name_plural = "Химические элементы"

    def __str__(self):
        return f"{self.element.symbol}: {self.min_value}–{self.max_value} %"
