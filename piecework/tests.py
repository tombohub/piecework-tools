import datetime as dt
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    Activity,
    DrywallRate,
    DrywallRateCategory,
    HeightCategory,
    RatePeriod,
    Unit,
    UnitDrywallMaterial,
    UnitSheetCount,
)


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

        twelve_foot_material = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
        )
        eight_foot_material = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.EIGHT,
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

        material = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
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

        completed_on = dt.date(2026, 10, 25)

        unit.mark_completed(completed_on=completed_on)
        unit.refresh_from_db()

        self.assertEqual(unit.status, Unit.Status.COMPLETED)
        self.assertEqual(unit.completed_on, completed_on)

    def test_drywall_rate_returns_matching_standard_rate(self):
        applicable_period = RatePeriod.objects.create(
            name="2025-2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )
        other_period = RatePeriod.objects.create(
            name="2026-2027",
            starts_on=dt.date(2026, 5, 1),
            ends_on=dt.date(2027, 4, 30),
        )

        expected_rate = DrywallRate.objects.create(
            rate_period=applicable_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3520"),
        )

        # Rates that must not be selected.
        DrywallRate.objects.create(
            rate_period=applicable_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.PREMIUM,
            rate=Decimal("0.4000"),
        )
        DrywallRate.objects.create(
            rate_period=applicable_period,
            height=HeightCategory.OVER_NINE_TO_TEN_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3750"),
        )
        DrywallRate.objects.create(
            rate_period=other_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3900"),
        )

        unit = Unit.objects.create(
            number="103",
            completed_on=dt.date(2025, 10, 25),
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
        )

        self.assertEqual(unit.drywall_rate, expected_rate.rate)


class UnitSheetCountTests(TestCase):
    def test_square_footage_is_calculated_correct(self):
        material = UnitDrywallMaterial(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
        )
        sheet_count = UnitSheetCount(drywall_material=material, count=10)

        self.assertEqual(sheet_count.square_footage, 480)


class UnitDrywallMaterialTests(TestCase):
    def test_square_footage_is_calculated_correctly(self):
        material = UnitDrywallMaterial(drywall_type="Regular", length_feet=12)

        self.assertEqual(material.square_footage, 48)


class RatePeriodTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.rate_period: RatePeriod = RatePeriod.objects.create(
            name="2025–2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )

    def test_get_for_date_returns_period_containin_date(self):
        result = RatePeriod.objects.get_for_date(dt.date(2025, 10, 25))

        self.assertEqual(result, self.rate_period)

    def test_get_for_date_includes_period_boundaries(self):
        for on_date in (self.rate_period.starts_on, self.rate_period.ends_on):
            with self.subTest(on_date=on_date):
                result = RatePeriod.objects.get_for_date(on_date)

                self.assertEqual(result, self.rate_period)

    def test_get_for_date_raises_when_no_period_containes_date(self):
        with self.assertRaises(RatePeriod.DoesNotExist):
            RatePeriod.objects.get_for_date(dt.date(2026, 5, 1))

    def test_get_for_date_raises_when_periods_overlap(self):
        RatePeriod.objects.create(
            name="Overlapping period",
            starts_on=dt.date(2025, 10, 1),
            ends_on=dt.date(2026, 9, 30),
        )

        with self.assertRaises(RatePeriod.MultipleObjectsReturned):
            RatePeriod.objects.get_for_date(dt.date(2025, 10, 25))
