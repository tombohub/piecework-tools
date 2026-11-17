"""Test names follow: test__<method_or_property>__<result>[_when_<condition>]."""

import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone

from .models import (
    Activity,
    ActivityLog,
    BoardingSprint,
    BoardingSprintSheetCount,
    BoardingSprintTimeLog,
    DrywallRate,
    DrywallRateCategory,
    HeightCategory,
    InsulationRate,
    JmouldRate,
    PotlightRate,
    Project,
    RatePeriod,
    SprinklerRate,
    Unit,
    UnitDrywallMaterial,
    UnitInsulationCount,
    UnitInsulationMaterial,
    UnitJmouldCount,
    UnitSheetCount,
)


class HomeViewTests(TestCase):
    def test__mark_complete__updates_active_unit(self):
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        self.client.post(
            reverse(
                "piecework:units_complete",
                kwargs={"pk": active_unit.pk},
            )
        )

        active_unit.refresh_from_db()
        self.assertEqual(active_unit.status, Unit.Status.COMPLETED)
        self.assertEqual(active_unit.completed_on, dt.date.today())

    def test__mark_complete__rejects_get_request(self):
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        response = self.client.get(
            reverse(
                "piecework:units_complete",
                kwargs={"pk": active_unit.pk},
            )
        )

        self.assertEqual(response.status_code, 405)

    def test__start_activity__rejects_get_request(self):
        Activity.objects.create(name="board")
        Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        response = self.client.get(
            reverse("piecework:start-activity"),
            {"action": "board"},
        )

        self.assertEqual(response.status_code, 405)
        self.assertFalse(ActivityLog.objects.exists())


class ActivityTests(TestCase):
    def test__requires_active_unit__returns_true_for_boarding(self):
        activity = Activity(category=Activity.Category.BOARDING)

        self.assertTrue(activity.requires_active_unit)

    def test__requires_active_unit__returns_false_for_other_activity(self):
        activity = Activity(category=Activity.Category.OTHER)

        self.assertFalse(activity.requires_active_unit)


class ActivityLogTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.unit = Unit.objects.create(number="101")
        cls.boarding = Activity.objects.create(
            name="Boarding",
            category=Activity.Category.BOARDING,
        )
        cls.break_activity = Activity.objects.create(
            name="Break", category=Activity.Category.OTHER
        )

    def test__current__returns_activity_log_without_end(self):
        activity_log = ActivityLog.objects.create(
            activity=self.break_activity, start=timezone.now()
        )

        result = ActivityLog.objects.current()

        self.assertEqual(result, activity_log)

    def test__current__returns_none_when_activity_has_ended(self):
        now = timezone.now()
        ActivityLog.objects.create(
            activity=self.break_activity, start=now - dt.timedelta(minutes=30), end=now
        )

        result = ActivityLog.objects.current()

        self.assertIsNone(result)

    def test__start__starts_other_activity_without_active_unit(self):
        activity_log = ActivityLog.objects.start(self.break_activity)

        self.assertEqual(activity_log.activity, self.break_activity)
        self.assertIsNone(activity_log.unit)
        self.assertIsNone(activity_log.end)

    def test__start__uses_active_unit_for_boarding(self):
        self.unit.status = Unit.Status.ACTIVE
        self.unit.save(update_fields=["status"])

        activity_log = ActivityLog.objects.start(self.boarding)

        self.assertEqual(activity_log.activity, self.boarding)
        self.assertEqual(activity_log.unit, self.unit)
        self.assertIsNone(activity_log.end)

    def test__start__raises_validation_error_when_boarding_has_no_active_unit(self):
        with self.assertRaisesMessage(
            ValidationError,
            "Boarding cannot start without an active unit.",
        ):
            ActivityLog.objects.start(self.boarding)
        self.assertFalse(ActivityLog.objects.exists())

    def test__start__stops_current_activity_before_starting_new_one(self):
        current_activity = ActivityLog.objects.create(
            activity=self.break_activity,
            start=timezone.now() - dt.timedelta(minutes=30),
        )

        new_activity = ActivityLog.objects.start(self.break_activity)

        current_activity.refresh_from_db()

        self.assertIsNotNone(current_activity.end)
        self.assertEqual(current_activity.end, new_activity.start)
        self.assertEqual(
            current_activity.duration, current_activity.end - current_activity.start
        )
        self.assertEqual(ActivityLog.objects.current(), new_activity)

    def test__start__preserves_current_activity_when_boarding_start_fails(self):
        current_activity = ActivityLog.objects.create(
            activity=self.break_activity,
            start=timezone.now(),
        )

        with self.assertRaises(ValidationError):
            ActivityLog.objects.start(self.boarding)

        current_activity.refresh_from_db()

        self.assertIsNone(current_activity.end)
        self.assertIsNone(current_activity.duration)
        self.assertEqual(ActivityLog.objects.current(), current_activity)

    def test__last_completed__returns_most_recent_completed_log(self):
        ActivityLog.objects.create(
            activity=self.boarding,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 9, 0),
            end=dt.datetime(2026, 11, 4, 10, 0),
        )

        expected_log = ActivityLog.objects.create(
            activity=self.break_activity,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 10, 0),
            end=dt.datetime(2026, 11, 4, 10, 30),
        )

        result = ActivityLog.objects.last_completed()
        assert result is not None

        self.assertEqual(result, expected_log)
        self.assertEqual(result.activity.name, "Break")
        self.assertEqual(result.duration, dt.timedelta(minutes=30))

    def test__last_completed__ignores_current_log(self):
        completed_log = ActivityLog.objects.create(
            activity=self.boarding,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 9, 0),
            end=dt.datetime(2026, 11, 4, 10, 0),
        )

        ActivityLog.objects.create(
            activity=self.break_activity,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 11, 0),
        )

        result = ActivityLog.objects.last_completed()

        self.assertEqual(result, completed_log)


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
            insulation_type=UnitInsulationMaterial.InsulationType.INTERIOR,
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

    def test__active_unit__returns_active_unit(self):
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

    def test__active_unit__returns_none_when_no_unit_is_active(self):
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

    def test__active_unit_constraint__rejects_second_active_unit(self):
        Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        with self.assertRaises(IntegrityError), transaction.atomic():
            Unit.objects.create(number="102", status=Unit.Status.ACTIVE)

        self.assertEqual(Unit.objects.filter(status=Unit.Status.ACTIVE).count(), 1)

    def test__total_square_footage__calculates_correctly(self):
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

    def test__drywall_price__returns_calculated_price(self):
        unit = self.create_unit()
        UnitSheetCount.objects.create(
            unit=unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )

        # 12 ft × 4 ft × 10 sheets = 480 sq ft
        # 480 sq ft × $0.3520 = $168.96
        self.assertEqual(unit.drywall_price, Decimal("168.96"))

    def test__jmould_price__returns_calculated_price(self):
        unit = self.create_unit()
        UnitJmouldCount.objects.create(unit=unit, length_feet=8, count=2)
        UnitJmouldCount.objects.create(unit=unit, length_feet=10, count=3)

        # (8 ft × 2) + (10 ft × 3) = 46 linear ft
        # 46 linear ft × $0.1250 = $5.75
        self.assertEqual(unit.jmould_price, Decimal("5.75"))

    def test__sprinkler_price__returns_calculated_price(self):
        unit = self.create_unit(sprinklers_count=8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.25 = $3.75
        self.assertEqual(unit.sprinkler_price, Decimal("3.75"))

    def test__potlight_price__returns_calculated_price(self):
        unit = self.create_unit(potlights_count=8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.50 = $4.50
        self.assertEqual(unit.potlight_price, Decimal("4.50"))

    def test__total_insulation_square_footage__returns_calculated_area(self):
        unit = self.create_unit()
        UnitInsulationCount.objects.create(
            unit=unit,
            insulation_material=self.insulation_material,
            count=2,
        )

        # 24 in × 48 in = 8 sq ft per piece
        # 8 sq ft × 2 pieces = 16 sq ft
        self.assertEqual(unit.total_insulation_square_footage, Decimal("16"))

    def test__insulation_price__returns_calculated_price(self):
        unit = self.create_unit()
        UnitInsulationCount.objects.create(
            unit=unit,
            insulation_material=self.insulation_material,
            count=2,
        )

        # 16 sq ft × $0.1850 = $2.96
        self.assertEqual(unit.insulation_price, Decimal("2.9600"))

    def test__total_price__returns_calculated_price(self):
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

    def test__mark_completed__updates_status(self):
        unit = Unit.objects.create(number="102", status=Unit.Status.ON_HOLD)

        completed_on = dt.date(2026, 10, 25)

        unit.mark_completed(completed_on=completed_on)
        unit.refresh_from_db()

        self.assertEqual(unit.status, Unit.Status.COMPLETED)
        self.assertEqual(unit.completed_on, completed_on)

    def test__drywall_rate__returns_matching_standard_rate(self):
        unit = self.create_unit(number="103")

        self.assertEqual(unit.drywall_rate, self.drywall_rate.rate)

    def test__weighted_sheets_per_hour__returns_weighted_rate(self):
        boarding = Activity.objects.create(name="board")

        first_unit = self.create_unit(
            number="101",
            status=Unit.Status.COMPLETED,
        )
        second_unit = self.create_unit(number="102", status=Unit.Status.COMPLETED)

        UnitSheetCount.objects.create(
            unit=first_unit,
            drywall_material=self.twelve_foot_material,
            count=20,
        )

        UnitSheetCount.objects.create(
            unit=second_unit,
            drywall_material=self.twelve_foot_material,
            count=40,
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=first_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
        )

        result = Unit.objects.weighted_sheets_per_hour()

        self.assertEqual(result, Decimal("12.00"))

    def test__weighted_sheets_per_hour__filters_by_project(self):
        boarding = Activity.objects.create(name="board")

        first_project = Project.objects.create(name="First project")
        second_project = Project.objects.create(name="Second project")

        first_unit = self.create_unit(
            number="101", status=Unit.Status.COMPLETED, project=first_project
        )

        second_unit = self.create_unit(
            number="102", status=Unit.Status.COMPLETED, project=second_project
        )

        UnitSheetCount.objects.create(
            unit=first_unit, drywall_material=self.twelve_foot_material, count=20
        )
        UnitSheetCount.objects.create(
            unit=second_unit,
            drywall_material=self.twelve_foot_material,
            count=40,
        )

        ActivityLog.objects.create(
            activity=boarding,
            unit=first_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
        )

        first_project_rate = Unit.objects.weighted_sheets_per_hour(
            project=first_project
        )
        second_project_rate = Unit.objects.weighted_sheets_per_hour(
            project=second_project
        )

        # First project: 20 sheets / 1 hour
        self.assertEqual(first_project_rate, Decimal("20.00"))

        # Second project: 40 sheets / 4 hours
        self.assertEqual(second_project_rate, Decimal("10.00"))

    def test__weighted_sheets_per_hour__returns_zero_for_project_without_data(self):
        project = Project.objects.create(name="Empty project")

        result = Unit.objects.weighted_sheets_per_hour(project=project)

        self.assertEqual(result, Decimal("0.00"))

    def test__weighted_sheets_per_hour__filters_by_height(self):
        boarding = Activity.objects.create(name="board")

        lower_unit = self.create_unit(
            number="101",
            status=Unit.Status.COMPLETED,
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
        )
        higher_unit = self.create_unit(
            number="102",
            status=Unit.Status.COMPLETED,
            height_feet=HeightCategory.OVER_NINE_TO_TEN_INCLUSIVE,
        )

        UnitSheetCount.objects.create(
            unit=lower_unit,
            drywall_material=self.twelve_foot_material,
            count=20,
        )
        UnitSheetCount.objects.create(
            unit=higher_unit,
            drywall_material=self.twelve_foot_material,
            count=40,
        )

        ActivityLog.objects.create(
            activity=boarding,
            unit=lower_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=higher_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
        )

        result = Unit.objects.weighted_sheets_per_hour(
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE
        )

        self.assertEqual(result, Decimal("20.0"))

    def test__weighted_square_feet_per_hour__returns_weighted_rate(self):
        boarding = Activity.objects.create(name="board")

        first_unit = self.create_unit(
            number="101",
            status=Unit.Status.COMPLETED,
        )
        second_unit = self.create_unit(
            number="102",
            status=Unit.Status.COMPLETED,
        )

        UnitSheetCount.objects.create(
            unit=first_unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitSheetCount.objects.create(
            unit=second_unit,
            drywall_material=self.eight_foot_material,
            count=10,
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=first_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 11, tzinfo=dt.UTC),
        )

        result = Unit.objects.weighted_square_feet_per_hour()

        # (480 sq ft + 320 sq ft) / 4 hours
        self.assertEqual(result, Decimal("200.00"))

    def test__weighted_square_feet_per_hour__filters_by_project(self):
        boarding = Activity.objects.create(name="board")
        first_project = Project.objects.create(name="First project")
        second_project = Project.objects.create(name="Second project")

        first_unit = self.create_unit(
            number="101",
            status=Unit.Status.COMPLETED,
            project=first_project,
        )
        second_unit = self.create_unit(
            number="102",
            status=Unit.Status.COMPLETED,
            project=second_project,
        )

        UnitSheetCount.objects.create(
            unit=first_unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitSheetCount.objects.create(
            unit=second_unit,
            drywall_material=self.eight_foot_material,
            count=10,
        )

        ActivityLog.objects.create(
            activity=boarding,
            unit=first_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 10, tzinfo=dt.UTC),
        )

        first_project_rate = Unit.objects.weighted_square_feet_per_hour(
            project=first_project
        )
        second_project_rate = Unit.objects.weighted_square_feet_per_hour(
            project=second_project
        )

        self.assertEqual(first_project_rate, Decimal("480.00"))
        self.assertEqual(second_project_rate, Decimal("160.00"))

    def test__weighted_square_feet_per_hour__returns_zero_for_project_without_data(
        self,
    ):
        project = Project.objects.create(name="Empty project")

        result = Unit.objects.weighted_square_feet_per_hour(project=project)

        self.assertEqual(result, Decimal("0.00"))

    def test__weighted_square_feet_per_hour__filters_by_height(self):
        boarding = Activity.objects.create(name="board")

        lower_unit = self.create_unit(
            number="101",
            status=Unit.Status.COMPLETED,
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
        )
        higher_unit = self.create_unit(
            number="102",
            status=Unit.Status.COMPLETED,
            height_feet=HeightCategory.OVER_NINE_TO_TEN_INCLUSIVE,
        )

        UnitSheetCount.objects.create(
            unit=lower_unit,
            drywall_material=self.twelve_foot_material,
            count=10,
        )
        UnitSheetCount.objects.create(
            unit=higher_unit,
            drywall_material=self.eight_foot_material,
            count=10,
        )

        ActivityLog.objects.create(
            activity=boarding,
            unit=lower_unit,
            start=dt.datetime(2025, 10, 20, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 20, 9, tzinfo=dt.UTC),
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=higher_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 10, tzinfo=dt.UTC),
        )

        result = Unit.objects.weighted_square_feet_per_hour(
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE
        )

        self.assertEqual(result, Decimal("480.00"))


class UnitSheetCountTests(TestCase):
    def test__square_footage__returns_material_area_times_count(self):
        material = UnitDrywallMaterial(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
        )
        sheet_count = UnitSheetCount(drywall_material=material, count=10)

        self.assertEqual(sheet_count.square_footage, 480)


class UnitDrywallMaterialTests(TestCase):
    def test__square_footage__returns_sheet_area(self):
        material = UnitDrywallMaterial(drywall_type="Regular", length_feet=12)

        self.assertEqual(material.square_footage, 48)


class SprinklerRateTests(SimpleTestCase):
    def setUp(self) -> None:
        self.sprinkler_rate = SprinklerRate(
            rate=Decimal("1.2500"),
            unpaid_quantity=5,
        )

    def test__price_for__excludes_unpaid_quantity(self):
        result = self.sprinkler_rate.price_for(8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.25 = $3.75
        self.assertEqual(result, Decimal("3.75"))

    def test__price_for__returns_zero_at_or_below_unpaid_quantity(self):
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

    def test__price_for__excludes_unpaid_quantity(self):
        result = self.potlight_rate.price_for(8)

        # 8 total - 5 unpaid = 3 payable
        # 3 x $1.50 = $4.50
        self.assertEqual(result, Decimal("4.50"))

    def test__price_for__returns_zero_at_or_below_unpaid_quantity(self):
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

    def test__get_for_date__returns_period_containing_date(self):
        result = RatePeriod.objects.get_for_date(dt.date(2025, 10, 25))

        self.assertEqual(result, self.rate_period)

    def test__get_for_date__includes_period_boundaries(self):
        for on_date in (self.rate_period.starts_on, self.rate_period.ends_on):
            with self.subTest(on_date=on_date):
                result = RatePeriod.objects.get_for_date(on_date)

                self.assertEqual(result, self.rate_period)

    def test__get_for_date__raises_when_no_period_contains_date(self):
        with self.assertRaises(RatePeriod.DoesNotExist):
            RatePeriod.objects.get_for_date(dt.date(2026, 5, 1))

    def test__get_for_date__raises_when_periods_overlap(self):
        RatePeriod.objects.create(
            name="Overlapping period",
            starts_on=dt.date(2025, 10, 1),
            ends_on=dt.date(2026, 9, 30),
        )

        with self.assertRaises(RatePeriod.MultipleObjectsReturned):
            RatePeriod.objects.get_for_date(dt.date(2025, 10, 25))


class InsulationRateTests(TestCase):
    def test__get_rate_value_for_period__returns_matching_rate(self):
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
    def test__square_footage__calculates_from_width_and_length(self):
        material = UnitInsulationMaterial(
            insulation_type=UnitInsulationMaterial.InsulationType.INTERIOR,
            width_inches=24,
            length_inches=48,
        )

        # 24 in × 48 in = 1,152 sq in
        # 1,152 ÷ 144 = 8 sq ft
        self.assertEqual(material.square_footage, Decimal("8"))

    def test__type_and_dimensions_constraint__rejects_duplicate_material(self):
        material_data = {
            "insulation_type": UnitInsulationMaterial.InsulationType.INTERIOR,
            "width_inches": 24,
            "length_inches": 48,
        }
        UnitInsulationMaterial.objects.create(**material_data)

        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitInsulationMaterial.objects.create(**material_data)

    def test__type_and_dimensions_constraint__allows_different_insulation_types(self):
        UnitInsulationMaterial.objects.create(
            insulation_type=UnitInsulationMaterial.InsulationType.INTERIOR,
            width_inches=24,
            length_inches=48,
        )

        material = UnitInsulationMaterial.objects.create(
            insulation_type=UnitInsulationMaterial.InsulationType.EXTERIOR,
            width_inches=24,
            length_inches=48,
        )

        self.assertEqual(
            material.insulation_type,
            UnitInsulationMaterial.InsulationType.EXTERIOR,
        )

    def test__insulation_type__has_expected_choices(self):
        self.assertEqual(
            UnitInsulationMaterial.InsulationType.choices,
            [
                ("interior", "Interior"),
                ("exterior", "Exterior"),
            ],
        )

    def test__insulation_type__rejects_unsupported_choice(self):
        material = UnitInsulationMaterial(
            insulation_type="unsupported",
            width_inches=24,
            length_inches=48,
        )

        with self.assertRaises(ValidationError):
            material.full_clean()


class UnitInsulationCountTests(SimpleTestCase):
    def test__square_footage__multiplies_material_area_by_count(self):
        material = UnitInsulationMaterial(
            insulation_type=UnitInsulationMaterial.InsulationType.INTERIOR,
            width_inches=24,
            length_inches=48,
        )
        insulation_count = UnitInsulationCount(
            insulation_material=material,
            count=3,
        )

        self.assertEqual(insulation_count.square_footage, Decimal("24"))


class UnitViewTests(TestCase):
    def test__unit_delete__removes_unit(self):
        unit = Unit.objects.create(number="101")
        delete_url = reverse("piecework:units_delete", kwargs={"pk": unit.pk})

        self.client.post(delete_url)

        self.assertFalse(Unit.objects.filter(pk=unit.pk).exists())

    def test__unit_delete__rejects_get_request(self):
        unit = Unit.objects.create(number="1")
        delete_url = reverse(
            "piecework:units_delete",
            kwargs={"pk": unit.pk},
        )

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Unit.objects.filter(pk=unit.pk).exists())

    def test__unit_delete__returns_404_for_unknown_unit(self):
        response = self.client.post(
            reverse("piecework:units_delete", kwargs={"pk": 99999})
        )

        self.assertEqual(response.status_code, 404)

    def test__units_create__saves_valid_unit(self):
        self.client.post(
            reverse("piecework:units_create"),
            {
                "number": "101",
                "status": Unit.Status.ACTIVE,
                "height_feet": (HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE),
            },
        )

        self.assertTrue(Unit.objects.filter(number="101").exists())

    def test__units_detail__returns_404_for_unknown_unit(self):
        response = self.client.get(
            reverse("piecework:units_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test__units_edit__updates_unit(self):
        unit = Unit.objects.create(
            number="101",
            status=Unit.Status.ON_HOLD,
        )

        self.client.post(
            reverse("piecework:units_edit", kwargs={"pk": unit.pk}),
            {
                "number": "102",
                "status": Unit.Status.ACTIVE,
                "height_feet": HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            },
        )

        unit.refresh_from_db()

        self.assertEqual(unit.number, "102")
        self.assertEqual(unit.status, Unit.Status.ACTIVE)


class ProjectTests(TestCase):
    def test__active_project__returns_active_project(self):
        Project.objects.create(
            name="Completed project",
            status=Project.ProjectStatus.COMPLETED,
        )
        active_project = Project.objects.create(
            name="Active project",
            status=Project.ProjectStatus.ACTIVE,
        )

        result = Project.objects.active_project()

        self.assertEqual(result, active_project)

    def test__active_project__returns_none_when_none_is_active(self):
        Project.objects.create(
            name="on hold porject", status=Project.ProjectStatus.ON_HOLD
        )

        result = Project.objects.active_project()

        self.assertIsNone(result)

    def test__active_project_constraint__rejects_second_active_project(self):
        Project.objects.create(
            name="First project",
            status=Project.ProjectStatus.ACTIVE,
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            Project.objects.create(
                name="Second project",
                status=Project.ProjectStatus.ACTIVE,
            )

        self.assertEqual(
            Project.objects.filter(status=Project.ProjectStatus.ACTIVE).count(), 1
        )

    def test__active_project_constraint__allows_multiple_non_active_projects(self):
        Project.objects.create(
            name="First project",
            status=Project.ProjectStatus.ON_HOLD,
        )
        Project.objects.create(
            name="Second project",
            status=Project.ProjectStatus.ON_HOLD,
        )

        self.assertEqual(Project.objects.count(), 2)


class BoardingSprintTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.unit = Unit.objects.create(number="101")
        cls.boarding = Activity.objects.create(name="board")
        cls.break_activity = Activity.objects.create(name="break")
        cls.twelve_foot_board = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.TWELVE,
        )
        cls.eight_foot_board = UnitDrywallMaterial.objects.get(
            drywall_type=UnitDrywallMaterial.DrywallType.REGULAR,
            length_feet=UnitDrywallMaterial.Length.EIGHT,
        )

    def _create_current_activity_log(self, activity: Activity) -> ActivityLog:
        return ActivityLog.objects.create(
            activity=activity, unit=self.unit, start=timezone.now()
        )

    def _create_boarding_activity_log(self) -> ActivityLog:
        return ActivityLog.objects.create(
            activity=self.boarding,
            unit=self.unit,
            start=timezone.now(),
        )

    def _create_stopped_boarding_sprint(self) -> BoardingSprint:
        activity_log = self._create_boarding_activity_log()

        return BoardingSprint.objects.create(
            activity_log=activity_log,
            status=BoardingSprint.Status.STOPPED,
        )

    def _create_break_activity_log(self) -> ActivityLog:
        return ActivityLog.objects.create(
            activity=self.break_activity,
            unit=self.unit,
            start=timezone.now(),
        )

    def test__current__returns_none_without_active_sprint(self):
        self.assertIsNone(BoardingSprint.objects.current())

    def test__current__returns_running_sprint(self):
        activity_log = self._create_current_activity_log(self.boarding)

        sprint = BoardingSprint.objects.create(
            activity_log=activity_log, status=BoardingSprint.Status.RUNNING
        )

        self.assertEqual(BoardingSprint.objects.current(), sprint)

    def test__current__returns_paused_sprint(self):
        activity_log = self._create_current_activity_log(self.boarding)

        sprint = BoardingSprint.objects.create(
            activity_log=activity_log, status=BoardingSprint.Status.PAUSED
        )

        self.assertEqual(BoardingSprint.objects.current(), sprint)

    def test__current__ignores_stopped_sprint(self):
        self._create_stopped_boarding_sprint()

        self.assertIsNone(BoardingSprint.objects.current())

    def test__can_start__returns_false_without_activity_log(self):
        self.assertFalse(BoardingSprint.objects.can_start(None))

    def test__can_start__returns_false_for_non_boarding_activity(self):
        activity_log = self._create_current_activity_log(self.break_activity)

        self.assertFalse(BoardingSprint.objects.can_start(activity_log))

    def test__can_start__returns_true_for_boarding_without_active_sprint(self):
        activity_log = self._create_current_activity_log(self.boarding)

        self.assertTrue(BoardingSprint.objects.can_start(activity_log))

    def test__can_start__returns_false_with_running_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()
        BoardingSprint.objects.create(
            activity_log=boarding_activity_log, status=BoardingSprint.Status.RUNNING
        )

        self.assertFalse(BoardingSprint.objects.can_start(boarding_activity_log))

    def test__can_start__returns_false_with_paused_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()
        BoardingSprint.objects.create(
            activity_log=boarding_activity_log, status=BoardingSprint.Status.PAUSED
        )

        self.assertFalse(BoardingSprint.objects.can_start(boarding_activity_log))

    def test__start_sprint__creates_running_sprint_and_time_log(self):
        boarding_activity_log = self._create_boarding_activity_log()
        before_start = timezone.now()

        sprint = BoardingSprint.objects.start_sprint()

        after_start = timezone.now()
        time_log = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint)

        self.assertEqual(sprint.activity_log, boarding_activity_log)
        self.assertEqual(sprint.status, BoardingSprint.Status.RUNNING)
        self.assertGreaterEqual(time_log.start_time, before_start)
        self.assertLessEqual(time_log.start_time, after_start)
        self.assertIsNone(time_log.end_time)

    def test__start_sprint__raises_without_current_activity(self):
        with self.assertRaisesMessage(
            ValidationError, "sprint cannot start without current activity"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertFalse(BoardingSprint.objects.exists())
        self.assertFalse(BoardingSprintTimeLog.objects.exists())

    def test__start_sprint__raises_for_non_boarding_activity(self):
        self._create_break_activity_log()

        with self.assertRaisesMessage(
            ValidationError, "A sprint can only start during boarding activity"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertFalse(BoardingSprint.objects.exists())
        self.assertFalse(BoardingSprintTimeLog.objects.exists())

    def test__start_sprint__rejects_second_active_sprint(self):
        self._create_boarding_activity_log()
        first_sprint = BoardingSprint.objects.start_sprint()

        with self.assertRaisesMessage(
            ValidationError, "A boarding sprint is already active"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertEqual(BoardingSprint.objects.count(), 1)
        self.assertEqual(BoardingSprintTimeLog.objects.count(), 1)
        self.assertEqual(BoardingSprint.objects.current(), first_sprint)

    def test__stop_sprint__closes_open_time_log_for_running_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        time_log = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint)
        before_stop = timezone.now()

        sprint.stop_sprint()

        after_stop = timezone.now()
        sprint.refresh_from_db()
        time_log.refresh_from_db()

        end_time = time_log.end_time
        assert end_time is not None

        self.assertEqual(sprint.status, BoardingSprint.Status.STOPPED)
        self.assertGreaterEqual(end_time, before_stop)
        self.assertLessEqual(end_time, after_stop)
        self.assertIsNone(BoardingSprint.objects.current())

    def test__stop_sprint__does_nothing_when_already_stopped(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint.stop_sprint()

        time_log = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint)
        original_end_time = time_log.end_time

        sprint.stop_sprint()

        sprint.refresh_from_db()
        time_log.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.STOPPED)
        self.assertEqual(time_log.end_time, original_end_time)

    def test__stop_sprint__does_not_create_time_log_for_paused_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()
        now = timezone.now()

        sprint = BoardingSprint.objects.create(
            activity_log=boarding_activity_log, status=BoardingSprint.Status.PAUSED
        )
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(minutes=20),
            end_time=now - dt.timedelta(minutes=10),
        )

        sprint.stop_sprint()

        sprint.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.STOPPED)
        self.assertEqual(
            BoardingSprintTimeLog.objects.filter(boarding_sprint=sprint).count(), 1
        )
        self.assertFalse(
            BoardingSprintTimeLog.objects.filter(
                boarding_sprint=sprint, end_time__isnull=True
            ).exists()
        )
        self.assertIsNone(BoardingSprint.objects.current())

    def test__stop_sprint__rejects_open_time_log_for_paused_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()

        sprint = BoardingSprint.objects.create(
            activity_log=boarding_activity_log,
            status=BoardingSprint.Status.PAUSED,
        )
        time_log = BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=timezone.now(),
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A paused boarding sprint cannot have an open time log",
        ):
            sprint.stop_sprint()

        sprint.refresh_from_db()
        time_log.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.PAUSED)
        self.assertIsNone(time_log.end_time)
        self.assertEqual(BoardingSprint.objects.current(), sprint)

    def test__stop_sprint__requires_open_time_log_for_running_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()

        sprint = BoardingSprint.objects.create(
            activity_log=boarding_activity_log, status=BoardingSprint.Status.RUNNING
        )

        with self.assertRaisesMessage(
            ValidationError, "The running boarding sprint has no open time log"
        ):
            sprint.stop_sprint()

        sprint.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.RUNNING)
        self.assertEqual(BoardingSprint.objects.current(), sprint)

    def test__pause_sprint__closes_open_time_log(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        time_log = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint)
        before_pause = timezone.now()

        sprint.pause_sprint()

        after_pause = timezone.now()
        sprint.refresh_from_db()
        time_log.refresh_from_db()

        end_time = time_log.end_time
        assert end_time is not None

        self.assertEqual(sprint.status, BoardingSprint.Status.PAUSED)
        self.assertGreaterEqual(end_time, before_pause)
        self.assertLessEqual(end_time, after_pause)
        self.assertEqual(BoardingSprint.objects.current(), sprint)
        self.assertFalse(
            BoardingSprintTimeLog.objects.filter(
                boarding_sprint=sprint, end_time__isnull=True
            ).exists()
        )

    def test__pause_sprint__does_nothing_when_already_paused(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint.pause_sprint()

        time_log = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint)
        original_end_time = time_log.end_time

        sprint.pause_sprint()

        sprint.refresh_from_db()
        time_log.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.PAUSED)
        self.assertEqual(time_log.end_time, original_end_time)

    def test__pause_sprint__rejects_stopped_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint.stop_sprint()

        with self.assertRaisesMessage(
            ValidationError,
            "Only a running boarding sprint can be paused",
        ):
            sprint.pause_sprint()

        sprint.refresh_from_db()

        self.assertEqual(
            sprint.status,
            BoardingSprint.Status.STOPPED,
        )

    def test__pause_sprint__requires_open_time_log(self):
        boarding_activity_log = self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.create(
            activity_log=boarding_activity_log,
            status=BoardingSprint.Status.RUNNING,
        )

        with self.assertRaisesMessage(
            ValidationError,
            "The running boarding sprint has no open time log",
        ):
            sprint.pause_sprint()

        sprint.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.RUNNING)
        self.assertEqual(BoardingSprint.objects.current(), sprint)

    def test__resume_sprint__creates_new_open_time_log(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint.pause_sprint()
        before_resume = timezone.now()

        sprint.resume_sprint()

        after_resume = timezone.now()
        sprint.refresh_from_db()

        open_time_log = BoardingSprintTimeLog.objects.get(
            boarding_sprint=sprint,
            end_time__isnull=True,
        )

        self.assertEqual(
            sprint.status,
            BoardingSprint.Status.RUNNING,
        )
        self.assertEqual(
            BoardingSprintTimeLog.objects.filter(boarding_sprint=sprint).count(),
            2,
        )
        self.assertGreaterEqual(
            open_time_log.start_time,
            before_resume,
        )
        self.assertLessEqual(
            open_time_log.start_time,
            after_resume,
        )
        self.assertEqual(
            BoardingSprint.objects.current(),
            sprint,
        )

    def test__resume_sprint__rejects_running_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()

        with self.assertRaisesMessage(
            ValidationError,
            "Only a paused boarding sprint can be resumed",
        ):
            sprint.resume_sprint()

        self.assertEqual(sprint.status, BoardingSprint.Status.RUNNING)
        self.assertEqual(
            BoardingSprintTimeLog.objects.filter(
                boarding_sprint=sprint,
                end_time__isnull=True,
            ).count(),
            1,
        )

    def test__resume_sprint__rejects_stopped_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint.stop_sprint()

        with self.assertRaisesMessage(
            ValidationError,
            "Only a paused boarding sprint can be resumed",
        ):
            sprint.resume_sprint()

        self.assertEqual(sprint.status, BoardingSprint.Status.STOPPED)
        self.assertFalse(
            BoardingSprintTimeLog.objects.filter(
                boarding_sprint=sprint,
                end_time__isnull=True,
            ).exists()
        )

    def test__resume_sprint__rejects_open_time_log(self):
        activity_log = self._create_boarding_activity_log()

        sprint = BoardingSprint.objects.create(
            activity_log=activity_log,
            status=BoardingSprint.Status.PAUSED,
        )
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=timezone.now(),
        )

        with self.assertRaisesMessage(
            ValidationError,
            "A paused boarding sprint cannot have an open time log",
        ):
            sprint.resume_sprint()

        sprint.refresh_from_db()

        self.assertEqual(sprint.status, BoardingSprint.Status.PAUSED)
        self.assertTrue(
            BoardingSprintTimeLog.objects.filter(
                boarding_sprint=sprint,
                end_time__isnull=True,
            ).exists()
        )

    def test__discard_sprint__deletes_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sprint_id = sprint.pk

        sprint.discard_sprint()

        self.assertFalse(BoardingSprint.objects.filter(pk=sprint_id).exists())

    def test__discard_sprint__deletes_time_logs(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        time_log_id = BoardingSprintTimeLog.objects.get(boarding_sprint=sprint).pk

        sprint.discard_sprint()

        self.assertFalse(BoardingSprintTimeLog.objects.filter(pk=time_log_id).exists())

    def test__discard_sprint__deletes_sheet_count(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        sheet_count = BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=5,
        )
        sheet_count_id = sheet_count.pk

        sprint.discard_sprint()

        self.assertFalse(
            BoardingSprintSheetCount.objects.filter(pk=sheet_count_id).exists()
        )

    def test__discard_sprint__preserves_activity_log(self):
        activity_log = self._create_boarding_activity_log()
        activity_log_id = activity_log.pk
        sprint = BoardingSprint.objects.start_sprint()

        sprint.discard_sprint()

        self.assertTrue(ActivityLog.objects.filter(pk=activity_log_id).exists())

    def test__discard_sprint__preserves_drywall_material(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()
        material_id = self.twelve_foot_board.pk
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=5,
        )

        sprint.discard_sprint()

        self.assertTrue(UnitDrywallMaterial.objects.filter(pk=material_id).exists())

    def test__can_start__returns_true_after_discarding_active_sprint(self):
        self._create_boarding_activity_log()
        sprint = BoardingSprint.objects.start_sprint()

        sprint.discard_sprint()
        new_sprint = BoardingSprint.objects.start_sprint()

        self.assertEqual(BoardingSprint.objects.current(), new_sprint)
        self.assertEqual(BoardingSprint.objects.count(), 1)

    def test__clean__rejects_non_boarding_activity(self):
        activity_log = self._create_break_activity_log()
        sprint = BoardingSprint(activity_log=activity_log)

        with self.assertRaisesMessage(
            ValidationError,
            "A boarding sprint must belong to boarding activity log",
        ):
            sprint.full_clean()

        self.assertFalse(BoardingSprint.objects.exists())

    def test__active_sprint_constraint__rejects_second_active_sprint(self):
        boarding_activity_log = self._create_boarding_activity_log()
        BoardingSprint.objects.create(
            activity_log=boarding_activity_log, status=BoardingSprint.Status.RUNNING
        )

        with self.assertRaises(IntegrityError), transaction.atomic():
            BoardingSprint.objects.create(
                activity_log=boarding_activity_log,
                status=BoardingSprint.Status.PAUSED,
            )

        self.assertEqual(BoardingSprint.objects.count(), 1)

    def test__duration__returns_zero_without_time_logs(self):
        sprint = self._create_stopped_boarding_sprint()

        self.assertEqual(sprint.duration, dt.timedelta())

    def test__duration__sums_time_logs_and_excludes_gaps(self):
        sprint = self._create_stopped_boarding_sprint()
        now = timezone.now()

        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(hours=3),
            end_time=now - dt.timedelta(hours=2),
        )
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(hours=1, minutes=30),
            end_time=now - dt.timedelta(hours=1),
        )

        result = sprint.duration
        expected = dt.timedelta(hours=1, minutes=30)
        self.assertEqual(result, expected)

    def test__duration__includes_elapsed_time_for_open_log(self):
        sprint = BoardingSprint.objects.create(
            activity_log=self._create_boarding_activity_log(),
            status=BoardingSprint.Status.RUNNING,
        )
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint, start_time=timezone.now() - dt.timedelta(minutes=30)
        )

        result = sprint.duration.total_seconds()
        expected = dt.timedelta(minutes=30).total_seconds()
        self.assertAlmostEqual(result, expected, delta=1)

    def test__sheet_count__sums_sheet_counts(self):
        sprint = self._create_stopped_boarding_sprint()
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=5,
        )
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.eight_foot_board,
            count=7,
        )

        expected = 12
        result = sprint.sheet_count

        self.assertEqual(expected, result)

    def test__sheet_count__returns_zero_without_sheet_counts(self):
        sprint = self._create_stopped_boarding_sprint()
        expected = 0

        result = sprint.sheet_count

        self.assertEqual(expected, result)

    def test__square_footage__sums_sheet_count_square_footage(self):
        sprint = self._create_stopped_boarding_sprint()
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=5,
        )
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.eight_foot_board,
            count=7,
        )

        result = sprint.square_footage

        # (12 ft × 4 ft × 5) + (8 ft × 4 ft × 7)
        self.assertEqual(result, 464)

    def test__square_footage__returns_zero_without_sheet_counts(self):
        sprint = self._create_stopped_boarding_sprint()

        result = sprint.square_footage

        self.assertEqual(result, 0)

    def test__sheets_per_hour__returns_average_sheets_per_hour(self):
        sprint = self._create_stopped_boarding_sprint()
        now = timezone.now()
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(minutes=30),
            end_time=now,
        )
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint, drywall_material=self.twelve_foot_board, count=10
        )

        expected = 20.0
        result = sprint.sheets_per_hour

        self.assertEqual(expected, result)

    def test__sheets_per_hour__returns_zero_without_duration(self):
        sprint = self._create_stopped_boarding_sprint()
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint, drywall_material=self.twelve_foot_board, count=10
        )

        expected = 0.0
        result = sprint.sheets_per_hour

        self.assertEqual(expected, result)

    def test__square_feet_per_hour__returns_average_square_feet_per_hour(self):
        sprint = self._create_stopped_boarding_sprint()
        now = timezone.now()
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(minutes=30),
            end_time=now,
        )
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=10,
        )

        result = sprint.square_feet_per_hour

        # 10 × 48 sq ft installed in half an hour
        self.assertEqual(result, 960.0)

    def test__square_feet_per_hour__returns_zero_without_duration(self):
        sprint = self._create_stopped_boarding_sprint()
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=10,
        )

        result = sprint.square_feet_per_hour

        self.assertEqual(result, 0.0)

    def test__dollars_per_hour__returns_estimated_earnings_per_hour(self):
        rate_period = RatePeriod.objects.create(
            name="2025-2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )
        DrywallRate.objects.create(
            rate_period=rate_period,
            height=self.unit.height_feet,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.5000"),
        )
        self.unit.started_on = dt.date(2025, 6, 1)
        self.unit.save(update_fields=["started_on"])

        sprint = self._create_stopped_boarding_sprint()
        now = timezone.now()
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(minutes=30),
            end_time=now,
        )
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=10,
        )

        result = sprint.dollars_per_hour

        # 10 × 48 sq ft ÷ 0.5 hours × $0.50/sq ft
        self.assertEqual(result, 480.0)

    def test__dollars_per_hour__returns_zero_without_duration(self):
        sprint = self._create_stopped_boarding_sprint()
        BoardingSprintSheetCount.objects.create(
            boarding_sprint=sprint,
            drywall_material=self.twelve_foot_board,
            count=10,
        )

        result = sprint.dollars_per_hour

        self.assertEqual(result, 0.0)

    def test__dollars_per_hour__returns_zero_without_sheet_counts(self):
        rate_period = RatePeriod.objects.create(
            name="2025-2026",
            starts_on=dt.date(2025, 5, 1),
            ends_on=dt.date(2026, 4, 30),
        )
        DrywallRate.objects.create(
            rate_period=rate_period,
            height=self.unit.height_feet,
            rate_category=DrywallRateCategory.STANDARD,
            rate=Decimal("0.5000"),
        )
        self.unit.started_on = dt.date(2025, 6, 1)
        self.unit.save(update_fields=["started_on"])

        sprint = self._create_stopped_boarding_sprint()
        now = timezone.now()
        BoardingSprintTimeLog.objects.create(
            boarding_sprint=sprint,
            start_time=now - dt.timedelta(minutes=30),
            end_time=now,
        )

        result = sprint.dollars_per_hour

        self.assertEqual(result, 0.0)
