from django.db import models
from django.contrib.contenttypes.fields import GenericRelation

from ..units.models import Unit, PhysicalQuantity
from ..language.models import Translation
from ..standards.models import StandardEdition


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
        unique_together = ("material", "standard", "symbol")

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
        "elements.Element",
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


class AbstractPropertyType(models.Model):
    """
    Abstract definition of a material property
    """

    key = models.CharField(max_length=50, unique=True)
    symbol = models.CharField(max_length=20, blank=True)

    physical_quantity = models.ForeignKey(
        PhysicalQuantity,
        on_delete=models.PROTECT
    )

    default_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT
    )

    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    translations = GenericRelation(Translation)

    class Meta:
        abstract = True
        ordering = ("sort_order", "key")
        constraints = [
            models.UniqueConstraint(
                fields=["key", "physical_quantity"],
                name="uniq_property_key_quantity"
            )
        ]

    def __str__(self):
        return self.key


class MechanicalPropertyType(AbstractPropertyType):
    class Meta:
        verbose_name = "Тип механического свойства"
        verbose_name_plural = "Типы механических свойств"


class PhysicalPropertyType(AbstractPropertyType):
    class Meta:
        verbose_name = "Тип физического свойства"
        verbose_name_plural = "Типы физических свойств"


class AbstractPropertySet(models.Model):
    material = models.ForeignKey(
        "Material",
        on_delete=models.CASCADE
    )

    standard_edition = models.ForeignKey(
        StandardEdition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    temperature_min = models.FloatField(null=True, blank=True)
    temperature_max = models.FloatField(null=True, blank=True)

    temperature_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="+"
    )

    class Meta:
        abstract = True


class MaterialMechanicalPropertySet(AbstractPropertySet):
    class Meta:
        verbose_name = "Набор механических свойств"
        verbose_name_plural = "Наборы механических свойств"


class MaterialPhysicalPropertySet(AbstractPropertySet):
    class Meta:
        verbose_name = "Набор физических свойств"
        verbose_name_plural = "Наборы физических свойств"


class AbstractPropertyValue(models.Model):
    min_value = models.FloatField()
    max_value = models.FloatField()

    unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT
    )

    class Meta:
        abstract = True


class MaterialMechanicalProperty(AbstractPropertyValue):
    property_set = models.ForeignKey(
        MaterialMechanicalPropertySet,
        on_delete=models.CASCADE,
        related_name="properties"
    )

    property_type = models.ForeignKey(
        MechanicalPropertyType,
        on_delete=models.PROTECT
    )

    class Meta:
        unique_together = ("property_set", "property_type")


class MaterialPhysicalProperty(AbstractPropertyValue):
    property_set = models.ForeignKey(
        MaterialPhysicalPropertySet,
        on_delete=models.CASCADE,
        related_name="properties"
    )

    property_type = models.ForeignKey(
        PhysicalPropertyType,
        on_delete=models.PROTECT
    )

    class Meta:
        unique_together = ("property_set", "property_type")


class HeatTreatmentType(models.Model):
    """
    Type of heat treatment
    (Annealing, Quenching, Tempering, Normalizing, etc.)
    """

    key = models.CharField(
        max_length=50,
        unique=True,
        help_text="annealing, quenching, tempering, solution_annealing"
    )

    sort_order = models.PositiveSmallIntegerField(default=0)
    is_active = models.BooleanField(default=True)

    translations = GenericRelation(Translation)

    class Meta:
        verbose_name = "Тип термообработки"
        verbose_name_plural = "Типы термообработки"
        ordering = ("sort_order", "key")

    def __str__(self):
        return self.key


class MaterialHeatTreatment(models.Model):
    """
    Heat treatment definition for a material
    """

    material = models.ForeignKey(
        Material,
        on_delete=models.CASCADE,
        related_name="heat_treatments"
    )

    heat_treatment_type = models.ForeignKey(
        HeatTreatmentType,
        on_delete=models.PROTECT,
        related_name="material_heat_treatments"
    )

    standard_edition = models.ForeignKey(
        StandardEdition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Standard defining this heat treatment"
    )

    is_recommended = models.BooleanField(
        default=True,
        help_text="Recommended / typical heat treatment"
    )

    notes = GenericRelation(Translation)

    class Meta:
        verbose_name = "Термообработка материала"
        verbose_name_plural = "Термообработки материалов"
        unique_together = ("material", "heat_treatment_type", "standard_edition")

    def __str__(self):
        return f"{self.material} – {self.heat_treatment_type}"


class HeatTreatmentStep(models.Model):
    """
    Single step of heat treatment
    (heating, holding, cooling)
    """

    heat_treatment = models.ForeignKey(
        MaterialHeatTreatment,
        on_delete=models.CASCADE,
        related_name="steps"
    )

    step_order = models.PositiveSmallIntegerField()

    temperature_min = models.FloatField(null=True, blank=True)
    temperature_max = models.FloatField(null=True, blank=True)

    temperature_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="+"
    )

    time_min = models.FloatField(null=True, blank=True)
    time_max = models.FloatField(null=True, blank=True)

    time_unit = models.ForeignKey(
        Unit,
        on_delete=models.PROTECT,
        related_name="+"
    )

    cooling_medium = models.CharField(
        max_length=50,
        blank=True,
        help_text="water, oil, air, furnace"
    )

    notes = GenericRelation(Translation)

    class Meta:
        verbose_name = "Шаг термообработки"
        verbose_name_plural = "Шаги термообработки"
        ordering = ("step_order",)

    def __str__(self):
        return f"Step {self.step_order}"
