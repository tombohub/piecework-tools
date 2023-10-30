from django.test import TestCase
from . import db
from .models import ActivityTime


# Create your tests here.
class GeneralTestCase(TestCase):
    def setUp(self):
        ActivityTime.objects.create(
            start="2021-06-01 00:00:00", end="2021-06-01 00:00:00"
        )

    def test_total_duration_today(self):
        self.assertEqual(db.total_duration_today(), 0)
