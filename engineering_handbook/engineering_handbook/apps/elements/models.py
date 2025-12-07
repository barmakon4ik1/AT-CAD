from django.db import models


# --- Группа по номеру (1–18) ---
class GroupNumber(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        verbose_name = "Номер группы"
        verbose_name_plural = "Номера группы"

    def __str__(self):
        return str(self.number)


# --- Группа по названию (например: "Алкали Металлы", "Halogens") ---
class GroupElement(models.Model):
    number = models.ForeignKey(GroupNumber, on_delete=models.CASCADE)
    title = models.CharField(max_length=100, blank=True)
    title_en = models.CharField(max_length=100, blank=True)
    title_ru = models.CharField(max_length=100, blank=True)
    title_de = models.CharField(max_length=100, blank=True)

    class Meta:
        verbose_name = "Химическая группа"
        verbose_name_plural = "Химические группы"

    def __str__(self):
        return self.title



# --- Период (1–7) ---
class Period(models.Model):
    number = models.PositiveSmallIntegerField(unique=True)

    class Meta:
        verbose_name = "Период"
        verbose_name_plural = "Периоды"

    def __str__(self):
        return str(self.number)


# --- Стандартное состояние (solid/liquid/gas/unknown) ---
class StandardState(models.Model):

    # machine-readable key ("solid", "liquid", ...)
    key = models.CharField(max_length=10, unique=True)

    # localized names
    name_en = models.CharField(max_length=50)
    name_ru = models.CharField(max_length=50)
    name_de = models.CharField(max_length=50)
    name_la = models.CharField(max_length=50)

    class Meta:
        verbose_name = "Стандартное состояние"
        verbose_name_plural = "Стандартные состояния"

    def __str__(self):
        return f"{self.key} ({self.name_ru})"



# --- Основная модель химического элемента ---
class Element(models.Model):
    BLOCK = [
        ("s", "s"), ("p", "p"), ("d", "d"), ("f", "f"),
    ]
    atomic_number = models.PositiveSmallIntegerField(unique=True)
    symbol = models.CharField(max_length=3, unique=True)

    # имена
    name = models.CharField(max_length=100, unique=True)
    name_en = models.CharField(max_length=100, blank=True)
    name_ru = models.CharField(max_length=100, blank=True)
    name_de = models.CharField(max_length=100, blank=True)

    atomic_mass = models.FloatField(null=True, blank=True)

    # периодическая таблица
    period = models.ForeignKey(Period, on_delete=models.SET_NULL, null=True, blank=True)
    group_number = models.ForeignKey(GroupNumber, on_delete=models.SET_NULL, null=True, blank=True)
    group = models.ForeignKey(GroupElement, on_delete=models.SET_NULL, null=True, blank=True)

    block = models.CharField(max_length=1, choices=BLOCK, null=True, blank=True)

    electron_configuration = models.CharField(max_length=50, blank=True)

    # физические свойства
    density = models.FloatField(null=True, blank=True)
    melting_point = models.FloatField(null=True, blank=True)
    boiling_point = models.FloatField(null=True, blank=True)

    oxidation_states = models.CharField(max_length=100, blank=True)
    electronegativity_pauling = models.FloatField(null=True, blank=True)

    standard_state = models.ForeignKey(StandardState, on_delete=models.SET_NULL, null=True, blank=True)

    color_hex = models.CharField(max_length=7, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['atomic_number']
        verbose_name = 'Элемент'
        verbose_name_plural = 'Элементы'

    def __str__(self):
        return f"{self.symbol} ({self.atomic_number})"
