from django.db import models


class PhysicalQuantity(models.Model):
    """
    Physical quantity, e.g. Length, Pressure, Temperature
    """
    key = models.CharField(max_length=50, unique=True)

    name_en = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100)

    symbol = models.CharField(
        max_length=20,
        blank=True,
        help_text="Common symbol, e.g. L, p, T"
    )

    class Meta:
        verbose_name = "Физическая величина"
        verbose_name_plural = "Физические величины"

    def __str__(self):
        return self.name_ru


class Unit(models.Model):
    """
    Measurement unit with conversion to base unit
    """
    quantity = models.ForeignKey(
        PhysicalQuantity,
        on_delete=models.CASCADE,
        related_name="units"
    )

    key = models.CharField(max_length=30)
    symbol = models.CharField(max_length=20)

    name_en = models.CharField(max_length=100)
    name_ru = models.CharField(max_length=100)
    name_de = models.CharField(max_length=100)

    is_base = models.BooleanField(default=False)

    # conversion to base unit:
    factor = models.FloatField(
        default=1.0,
        help_text="Multiplier to convert to base unit"
    )
    offset = models.FloatField(
        default=0.0,
        help_text="Offset added after multiplication"
    )

    class Meta:
        unique_together = ("quantity", "key")
        verbose_name = "Единица измерения"
        verbose_name_plural = "Единицы измерения"

    def __str__(self):
        return f"{self.symbol} ({self.name_ru})"


def convert_value(value, from_unit, to_unit):
    if from_unit.quantity_id != to_unit.quantity_id:
        raise ValueError("Incompatible physical quantities")

    # to base
    base_value = value * from_unit.factor + from_unit.offset

    # from base
    return (base_value - to_unit.offset) / to_unit.factor
