import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase

from .models import (
    Activity,
    DrywallRate,
    DrywallRateCategory,
    HeightCategory,
    InsulationRate,
    JmouldRate,
    PotlightRate,
    RatePeriod,
    SprinklerRate,
    Unit,
    UnitDrywallMaterial,
    UnitInsulationCount,
    UnitInsulationMaterial,
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
        SprinklerRate.objects.create(
            rate_period=cls.rate_period,
            rate=Decimal("1.2500"),
            unpaid_quantity=5,
        )
        PotlightRate.objects.create(
            rate_period=cls.rate_period,
            rate=Decimal("1.5000"),
            unpaid_quantity=5,
        )
        InsulationRate.objects.create(
            rate_period=cls.rate_period,
            rate=Decimal("0.1850"),
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
        cls.insulation_material = UnitInsulationMaterial.objects.create(
            thickness_inches=(UnitInsulationMaterial.Thickness.THREE_AND_FIVE_EIGHTHS),
            width_inches=24,
            length_inches=48,
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

        result = Unit.objects.active_unit()

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

        result = Unit.objects.active_unit()

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

    def test_sprinkler_price_is_calculated(self):
        unit = self.create_unit(sprinklers_count=8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.25 = $3.75
        self.assertEqual(unit.sprinkler_price, Decimal("3.75"))

    def test_potlight_price_is_calculated(self):
        unit = self.create_unit(potlights_count=8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.50 = $4.50
        self.assertEqual(unit.potlight_price, Decimal("4.50"))

    def test_total_insulation_square_footage_is_calculated(self):
        unit = self.create_unit()
        UnitInsulationCount.objects.create(
            unit=unit,
            insulation_material=self.insulation_material,
            count=2,
        )

        # 24 in × 48 in = 8 sq ft per piece
        # 8 sq ft × 2 pieces = 16 sq ft
        self.assertEqual(unit.total_insulation_square_footage, Decimal("16"))

    def test_insulation_price_is_calculated(self):
        unit = self.create_unit()
        UnitInsulationCount.objects.create(
            unit=unit,
            insulation_material=self.insulation_material,
            count=2,
        )

        # 16 sq ft × $0.1850 = $2.96
        self.assertEqual(unit.insulation_price, Decimal("2.9600"))

    def test_total_price_is_calculated(self):
        unit = self.create_unit(
            sprinklers_count=8,
            potlights_count=8,
        )
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitJmouldCount.objects.create(unit=unit, length_feet=8, count=2)
        UnitJmouldCount.objects.create(unit=unit, length_feet=10, count=3)
        UnitInsulationCount.objects.create(
            unit=unit,
            insulation_material=self.insulation_material,
            count=2,
        )

        # $168.96 drywall + $5.75 J-mould + $3.75 sprinklers
        # + $4.50 potlights + $2.96 insulation = $185.92
        self.assertEqual(unit.total_price, Decimal("185.92"))

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


class SprinklerRateTests(SimpleTestCase):
    def setUp(self) -> None:
        self.sprinkler_rate = SprinklerRate(
            rate=Decimal("1.2500"),
            unpaid_quantity=5,
        )

    def test_price_for_excludes_unpaid_quantity(self):
        result = self.sprinkler_rate.price_for(8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.25 = $3.75
        self.assertEqual(result, Decimal("3.75"))

    def test_price_for_returns_zero_at_or_below_unpaid_quantity(self):
        for quantity in (0, 3, 5):
            with self.subTest(quantity=quantity):
                result = self.sprinkler_rate.price_for(quantity)

                self.assertEqual(result, Decimal(0))


class PotlightRateTests(SimpleTestCase):
    def setUp(self) -> None:
        self.potlight_rate = PotlightRate(
            rate=Decimal("1.5000"),
            unpaid_quantity=5,
        )

    def test_price_for_excludes_unpaid_quantity(self):
        result = self.potlight_rate.price_for(8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.50 = $4.50
        self.assertEqual(result, Decimal("4.50"))

    def test_price_for_returns_zero_at_or_below_unpaid_quantity(self):
        for quantity in (0, 3, 5):
            with self.subTest(quantity=quantity):
                result = self.potlight_rate.price_for(quantity)

                self.assertEqual(result, Decimal(0))


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


class InsulationRateTests(TestCase):
    def test_get_rate_value_for_period_returns_matching_rate(self):
        rate_period = RatePeriod.objects.create(
            name="2025-2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )
        InsulationRate.objects.create(
            rate_period=rate_period,
            rate=Decimal("0.1850"),
        )

        result = InsulationRate.objects.get_rate_value_for_period(rate_period)

        self.assertEqual(result, Decimal("0.1850"))


class UnitInsulationMaterialTests(TestCase):
    def test_square_footage_is_calculated_from_width_and_length(self):
        material = UnitInsulationMaterial(
            thickness_inches=UnitInsulationMaterial.Thickness.THREE_AND_FIVE_EIGHTHS,
            width_inches=24,
            length_inches=48,
        )

        # 24 in × 48 in = 1,152 sq in
        # 1,152 ÷ 144 = 8 sq ft
        self.assertEqual(material.square_footage, Decimal("8"))

    def test_dimensions_must_be_unique(self):
        dimensions = {
            "thickness_inches": (
                UnitInsulationMaterial.Thickness.THREE_AND_FIVE_EIGHTHS
            ),
            "width_inches": 24,
            "length_inches": 48,
        }
        UnitInsulationMaterial.objects.create(**dimensions)

        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitInsulationMaterial.objects.create(**dimensions)

    def test_same_width_and_length_allow_different_thickness(self):
        UnitInsulationMaterial.objects.create(
            thickness_inches=UnitInsulationMaterial.Thickness.THREE_AND_FIVE_EIGHTHS,
            width_inches=24,
            length_inches=48,
        )

        material = UnitInsulationMaterial.objects.create(
            thickness_inches=UnitInsulationMaterial.Thickness.TWO_AND_ONE_HALF,
            width_inches=24,
            length_inches=48,
        )

        self.assertEqual(
            material.thickness_inches,
            UnitInsulationMaterial.Thickness.TWO_AND_ONE_HALF,
        )

    def test_thickness_has_expected_choices(self):
        self.assertEqual(
            UnitInsulationMaterial.Thickness.choices,
            [
                ("1_5_8", "1 5/8 inches"),
                ("2_1_2", "2 1/2 inches"),
                ("3_5_8", "3 5/8 inches"),
            ],
        )

    def test_thickness_must_be_one_of_the_choices(self):
        material = UnitInsulationMaterial(
            thickness_inches="unsupported",
            width_inches=24,
            length_inches=48,
        )

        with self.assertRaises(ValidationError):
            material.full_clean()


class UnitInsulationCountTests(SimpleTestCase):
    def test_square_footage_multiplies_material_area_by_count(self):
        material = UnitInsulationMaterial(
            thickness_inches=UnitInsulationMaterial.Thickness.ONE_AND_FIVE_EIGHTHS,
            width_inches=24,
            length_inches=48,
        )
        insulation_count = UnitInsulationCount(
            insulation_material=material,
            count=3,
        )

        self.assertEqual(insulation_count.square_footage, Decimal("24"))
