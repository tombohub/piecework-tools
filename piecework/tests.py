import datetime as dt
from decimal import Decimal

from django.db import IntegrityError, transaction
from django.test import TestCase

from .models import (
    Activity,
    DrywallRate,
    DrywallRateCategory,
    HeightCategory,
    JmouldRate,
    RatePeriod,
    Unit,
    UnitDrywallMaterial,
    UnitJmouldCount,
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
    @classmethod
    def setUpTestData(cls) -> None:
        cls.rate_period = RatePeriod.objects.create(
            name="2025-2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )
        cls.other_rate_period = RatePeriod.objects.create(
            name="2026-2027",
            starts_on=dt.date(2026, 5, 1),
            ends_on=dt.date(2027, 4, 30),
        )

        cls.drywall_rate = DrywallRate.objects.create(
            rate_period=cls.rate_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3520"),
        )
        JmouldRate.objects.create(
            rate_period=cls.rate_period,
            rate=Decimal("0.1250"),
        )

        # Rates that must not be selected for the default test unit.
        DrywallRate.objects.create(
            rate_period=cls.rate_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.PREMIUM,
            rate=Decimal("0.4000"),
        )
        DrywallRate.objects.create(
            rate_period=cls.rate_period,
            height=HeightCategory.OVER_NINE_TO_TEN_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3750"),
        )
        DrywallRate.objects.create(
            rate_period=cls.other_rate_period,
            height=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.3900"),
        )

        cls.twelve_foot_material = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
        )
        cls.eight_foot_material = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.EIGHT,
        )

    def create_unit(self, number: str = "101", **kwargs) -> Unit:
        defaults = {
            "completed_on": dt.date(2025, 10, 25),
            "height_feet": HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
        }
        defaults.update(kwargs)

        return Unit.objects.create(number=number, **defaults)

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

        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.eight_foot_material,
            count=5,
        )

        self.assertEqual(unit.total_square_footage, 640)

    def test_drywall_price_is_calculated(self):
        unit = self.create_unit()
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )

        # 12 ft × 4 ft × 10 sheets = 480 sq ft
        # 480 sq ft × $0.3520 = $168.96
        self.assertEqual(unit.drywall_price, Decimal("168.96"))

    def test_jmould_price_is_calculated(self):
        unit = self.create_unit()
        UnitJmouldCount.objects.create(unit=unit, length_feet=8, count=2)
        UnitJmouldCount.objects.create(unit=unit, length_feet=10, count=3)

        # (8 ft × 2) + (10 ft × 3) = 46 linear ft
        # 46 linear ft × $0.1250 = $5.75
        self.assertEqual(unit.jmould_price, Decimal("5.75"))

    def test_total_price_is_calculated(self):
        unit = self.create_unit()
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitJmouldCount.objects.create(unit=unit, length_feet=8, count=2)
        UnitJmouldCount.objects.create(unit=unit, length_feet=10, count=3)

        self.assertEqual(unit.total_price, Decimal("174.71"))

    def test_mark_completed_updates_status(self):
        unit = Unit.objects.create(number="102", status=Unit.Status.ON_HOLD)

        completed_on = dt.date(2026, 10, 25)

        unit.mark_completed(completed_on=completed_on)
        unit.refresh_from_db()

        self.assertEqual(unit.status, Unit.Status.COMPLETED)
        self.assertEqual(unit.completed_on, completed_on)

    def test_drywall_rate_returns_matching_standard_rate(self):
        unit = self.create_unit(number="103")

        self.assertEqual(unit.drywall_rate, self.drywall_rate.rate)


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
