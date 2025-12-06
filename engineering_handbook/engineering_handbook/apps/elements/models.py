from django.db import models

class Element(models.Model):
    atomic_number = models.PositiveSmallIntegerField(unique=True)
    symbol = models.CharField(max_length=3, unique=True)


    name = models.CharField(max_length=100, unique=True )
    name_en = models.CharField(max_length=100, blank=True)
    name_ru = models.CharField(max_length=100, blank=True)
    name_de = models.CharField(max_length=100, blank=True)


    atomic_mass = models.FloatField(null=True, blank=True, help_text='Standard atomic weight (u)')
    period = models.PositiveSmallIntegerField(null=True, blank=True)
    group = models.CharField(max_length=10, null=True, blank=True)
    block = models.CharField(max_length=1, null=True, blank=True)


    category = models.CharField(max_length=50, blank=True, help_text='metal / nonmetal / metalloid / noble gas / lanthanoid / actinoid')


    # optional physical properties
    density = models.FloatField(null=True, blank=True, help_text='g/cm^3 at 20°C (if applicable)')
    melting_point = models.FloatField(null=True, blank=True, help_text='°C')
    boiling_point = models.FloatField(null=True, blank=True, help_text='°C')


    oxidation_states = models.CharField(max_length=100, blank=True)
    electronegativity_pauling = models.FloatField(null=True, blank=True)


    color_hex = models.CharField(max_length=7, blank=True)


    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


    class Meta:
        ordering = ['atomic_number']
        verbose_name = 'Element'
        verbose_name_plural = 'Elements'


    def __str__(self):
        return f"{self.symbol} ({self.atomic_number})"
