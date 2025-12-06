from django.test import TestCase
from .models import Element


class ElementModelTest(TestCase):
    def test_create_element(self):
        e = Element.objects.create(atomic_number=999, symbol='Xx', name_en='Xxium')
        self.assertEqual(e.symbol, 'Xx')
        e.delete()
