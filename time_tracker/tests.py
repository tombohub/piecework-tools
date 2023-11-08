from django.test import TestCase
from . import db
from .models import ActivityLog


# Create your tests here.
class GeneralTestCase(TestCase):
    def test_kokoloko(self):
        assert True

    def test_fail(self):
        """
        Test if its False
        """
        assert False
