from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import Activity, DrywallMaterial, Unit, UnitSheetCount


class ActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        Activity.objects.create(name="Boarding")
        Activity.objects.create(name="Taping")

    def test_names_returns_activity_names(self):
        names = Activity.objects.names()

        self.assertCountEqual(names, ["Boarding", "Taping"])


class UnitTests(TestCase):
    def test_active_returns_active_unit(self):
        Unit.objects.create(
            number="101",
            status=Unit.Status.COMPLETED,
        )
        active_unit = Unit.objects.create(
            number="102",
            status=Unit.Status.ACTIVE,
        )

        result = Unit.objects.active()

        self.assertEqual(result, active_unit)

    def test_active_returns_none_when_no_unit_is_active(self):
        Unit.objects.create(
            number="101",
            status=Unit.Status.COMPLETED,
        )
        Unit.objects.create(
            number="102",
            status=Unit.Status.ON_HOLD,
        )

        result = Unit.objects.active()

        self.assertIsNone(result)

    def test_only_one_unit_can_be_active(self):
        Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Unit.objects.create(number="102", status=Unit.Status.ACTIVE)

        self.assertEqual(Unit.objects.filter(status=Unit.Status.ACTIVE).count(), 1)

    def test_total_unit_square_footage_calculates_correct(self):
        unit = Unit.objects.create(number="101")

        twelve_foot_material = DrywallMaterial.objects.get(
            drywall_type=DrywallMaterial.DrywallType.REGULAR,
            length_feet=DrywallMaterial.Length.TWELVE,
        )
        eight_foot_material = DrywallMaterial.objects.get(
            drywall_type=DrywallMaterial.DrywallType.REGULAR,
            length_feet=DrywallMaterial.Length.EIGHT,
        )

        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=twelve_foot_material,
            count=10,
        )
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=eight_foot_material,
            count=5,
        )

        self.assertEqual(unit.total_square_footage, 640)

    def test_total_price_is_calculated(self):
        unit = Unit.objects.create(number="101")

        material = DrywallMaterial.objects.get(
            drywall_type=DrywallMaterial.DrywallType.REGULAR,
            length_feet=DrywallMaterial.Length.TWELVE,
        )

        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=material,
            count=10,
        )

        # 12 × 4 × 10 = 480 square feet
        # 480 × 0.352 = 168.96
        self.assertEqual(unit.total_price, 168.96)

    def test_mark_completed_updates_status(self):
        unit = Unit.objects.create(number="102", status=Unit.Status.ON_HOLD)

        unit.mark_completed()
        unit.refresh_from_db()

        self.assertEqual(unit.status, Unit.Status.COMPLETED)


class UnitSheetCountTests(TestCase):
    def test_square_footage_is_calculated_correct(self):
        material = DrywallMaterial(
            drywall_type=DrywallMaterial.DrywallType.REGULAR,
            length_feet=DrywallMaterial.Length.TWELVE,
        )
        sheet_count = UnitSheetCount(drywall_material=material, count=10)

        self.assertEqual(sheet_count.square_footage, 480)


class UnitDrywallMaterialTests(TestCase):
    def test_square_footage_is_calculated_correctly(self):
        material = DrywallMaterial(drywall_type="Regular", length_feet=12)

        self.assertEqual(material.square_footage, 48)
