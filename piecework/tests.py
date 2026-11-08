import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from django.utils import timezone
from numpy import number

from piecework.forms import UnitForm

from .models import (
    Activity,
    ActivityLog,
    BoardingSprint,
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
    def test_mark_complete_updates_active_unit(self):
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

    def test_mark_complete_rejects_get_request(self):
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        response = self.client.get(
            reverse(
                "piecework:units_complete",
                kwargs={"pk": active_unit.pk},
            )
        )

        self.assertEqual(response.status_code, 405)

    def test_start_activity_uses_active_unit(self):
        activity = Activity.objects.create(name="board")
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)
        Unit.objects.create(number="102", status=Unit.Status.ON_HOLD)

        self.client.get(
            reverse("piecework:start-activity"),
            {"action": activity.name},
        )

        self.assertEqual(ActivityLog.objects.get().unit, active_unit)


class ActivityTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        Activity.objects.create(name="Boarding")
        Activity.objects.create(name="Taping")

    def test_names_returns_activity_names(self):
        names = Activity.objects.names()

        self.assertCountEqual(names, ["Boarding", "Taping"])


class ActivityLogTests(TestCase):
    @classmethod
    def setUpTestData(cls) -> None:
        cls.unit = Unit.objects.create(number="101")
        cls.boarding = Activity.objects.create(name="Boarding")
        cls.break_activity = Activity.objects.create(name="Break")

    def test_last_completed_returns_most_recent_completed_log(self):
        ActivityLog.objects.create(
            activity=self.boarding,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 9, 0),
            end=dt.datetime(2026, 11, 4, 10, 0),
            is_current=False,
        )

        expected_log = ActivityLog.objects.create(
            activity=self.break_activity,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 10, 0),
            end=dt.datetime(2026, 11, 4, 10, 30),
            is_current=False,
        )

        result = ActivityLog.objects.last_completed()
        assert result is not None

        self.assertEqual(result, expected_log)
        self.assertEqual(result.activity.name, "Break")
        self.assertEqual(result.duration, dt.timedelta(minutes=30))

    def test_last_completed_ignores_current_log(self):
        completed_log = ActivityLog.objects.create(
            activity=self.boarding,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 9, 0),
            end=dt.datetime(2026, 11, 4, 10, 0),
            is_current=False,
        )

        ActivityLog.objects.create(
            activity=self.break_activity,
            unit=self.unit,
            start=dt.datetime(2026, 11, 4, 11, 0),
            is_current=True,
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

    def test_weighted_sheets_per_hour(self):
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
            is_current=False,
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
            is_current=False,
        )

        result = Unit.objects.weighted_sheets_per_hour()

        self.assertEqual(result, Decimal("12.00"))

    def test_weighted_sheets_per_hour_filters_by_project(self):
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
            is_current=False,
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=second_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
            is_current=False,
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

    def test_weighted_sheets_per_hour_returns_zero_for_project_without_data(self):
        project = Project.objects.create(name="Empty project")

        result = Unit.objects.weighted_sheets_per_hour(project=project)

        self.assertEqual(result, Decimal("0.00"))

    def test_weighted_sheets_per_hour_filters_by_height(self):
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
            is_current=False,
        )
        ActivityLog.objects.create(
            activity=boarding,
            unit=higher_unit,
            start=dt.datetime(2025, 10, 21, 8, tzinfo=dt.UTC),
            end=dt.datetime(2025, 10, 21, 12, tzinfo=dt.UTC),
            is_current=False,
        )

        result = Unit.objects.weighted_sheets_per_hour(
            height_feet=HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE
        )

        self.assertEqual(result, Decimal("20.0"))


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
            insulation_type=UnitInsulationMaterial.InsulationType.INTERIOR,
            width_inches=24,
            length_inches=48,
        )

        # 24 in × 48 in = 1,152 sq in
        # 1,152 ÷ 144 = 8 sq ft
        self.assertEqual(material.square_footage, Decimal("8"))

    def test_type_and_dimensions_must_be_unique(self):
        material_data = {
            "insulation_type": UnitInsulationMaterial.InsulationType.INTERIOR,
            "width_inches": 24,
            "length_inches": 48,
        }
        UnitInsulationMaterial.objects.create(**material_data)

        with self.assertRaises(IntegrityError), transaction.atomic():
            UnitInsulationMaterial.objects.create(**material_data)

    def test_same_dimensions_allow_different_insulation_types(self):
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

    def test_insulation_type_has_expected_choices(self):
        self.assertEqual(
            UnitInsulationMaterial.InsulationType.choices,
            [
                ("interior", "Interior"),
                ("exterior", "Exterior"),
            ],
        )

    def test_insulation_type_must_be_one_of_the_choices(self):
        material = UnitInsulationMaterial(
            insulation_type="unsupported",
            width_inches=24,
            length_inches=48,
        )

        with self.assertRaises(ValidationError):
            material.full_clean()


class UnitInsulationCountTests(SimpleTestCase):
    def test_square_footage_multiplies_material_area_by_count(self):
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
    def test_unit_delete_removes_unit(self):
        unit = Unit.objects.create(number="101")
        delete_url = reverse("piecework:units_delete", kwargs={"pk": unit.pk})

        self.client.post(delete_url)

        self.assertFalse(Unit.objects.filter(pk=unit.pk).exists())

    def test_unit_delete_rejects_get_request(self):
        unit = Unit.objects.create(number="1")
        delete_url = reverse(
            "piecework:units_delete",
            kwargs={"pk": unit.pk},
        )

        response = self.client.get(delete_url)

        self.assertEqual(response.status_code, 405)
        self.assertTrue(Unit.objects.filter(pk=unit.pk).exists())

    def test_unit_delete_returns_404_for_uknown_unit(self):
        response = self.client.post(
            reverse("piecework:units_delete", kwargs={"pk": 99999})
        )

        self.assertEqual(response.status_code, 404)

    def test_units_create_saves_valid_unit(self):
        self.client.post(
            reverse("piecework:units_create"),
            {
                "number": "101",
                "status": Unit.Status.ACTIVE,
                "height_feet": (HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE),
            },
        )

        self.assertTrue(Unit.objects.filter(number="101").exists())

    def test_units_detail_returns_404_for_uknown_unit(self):
        response = self.client.get(
            reverse("piecework:units_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_units_updates_unit(self):
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
    def test_active_project_returns_active_project(self):
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

    def test_active_project_returns_none_when_none_is_active(self):
        Project.objects.create(
            name="on hold porject", status=Project.ProjectStatus.ON_HOLD
        )

        result = Project.objects.active_project()

        self.assertIsNone(result)

    def test_only_one_project_can_be_active(self):
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

    def test_multiple_non_active_projects_are_allowed(self):
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

    def _create_current_activity_log(self, activity: Activity) -> ActivityLog:
        return ActivityLog.objects.create(
            activity=activity, unit=self.unit, start=timezone.now(), is_current=True
        )

    def test_start_sprint_creates_sprint_for_current_boarding_activity(self):
        activity_log = self._create_current_activity_log(self.boarding)
        before_start = timezone.now()

        sprint = BoardingSprint.objects.start_sprint()
        after_start = timezone.now()

        self.assertEqual(sprint.activity_log, activity_log)
        self.assertGreaterEqual(sprint.start_time, before_start)
        self.assertLessEqual(sprint.start_time, after_start)
        self.assertIsNone(sprint.end_time)
        self.assertIsNone(sprint.sheets_installed)

    def test_start_sprint_require_current_activity(self):
        with self.assertRaisesMessage(
            ValidationError, "sprint cannot start without current activity"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertFalse(BoardingSprint.objects.exists())

    def test_start_sprint_requires_boarding_activity(self):
        self._create_current_activity_log(self.break_activity)

        with self.assertRaisesMessage(
            ValidationError, "A sprint can only start during boarding activity"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertFalse(BoardingSprint.objects.exists())

    def test_start_sprint_rejects_second_running_sprint(self):
        self._create_current_activity_log(self.boarding)
        first_sprint = BoardingSprint.objects.start_sprint()

        with self.assertRaisesMessage(
            ValidationError, "A boarding sprint is already running"
        ):
            BoardingSprint.objects.start_sprint()

        self.assertEqual(BoardingSprint.objects.count(), 1)
        self.assertEqual(BoardingSprint.objects.current(), first_sprint)

    def test_current_returns_none_without_running_sprint(self):
        self.assertIsNone(BoardingSprint.objects.current())

    def test_current_ignores_completed_sprint(self):
        activity_log = self._create_current_activity_log(self.boarding)
        now = timezone.now()

        BoardingSprint.objects.create(
            activity_log=activity_log,
            start_time=now - dt.timedelta(minutes=30),
            end_time=now,
            sheets_installed=10,
        )

        self.assertIsNone(BoardingSprint.objects.current())

    def test_stop_sprint_records_end_time_and_sheets_installed(self):
        self._create_current_activity_log(self.boarding)
        sprint = BoardingSprint.objects.start_sprint()
        before_stop = timezone.now()

        sprint.stop_sprint(sheets_installed=12)
        after_stop = timezone.now()

        sprint.refresh_from_db()
        end_time = sprint.end_time
        assert end_time is not None

        self.assertEqual(sprint.sheets_installed, 12)
        self.assertGreaterEqual(end_time, before_stop)
        self.assertLessEqual(end_time, after_stop)
        self.assertIsNone(BoardingSprint.objects.current())

    def test_stop_sprint_rejects_already_stopped_sprint(self):
        self._create_current_activity_log(self.boarding)
        sprint = BoardingSprint.objects.start_sprint()
        sprint.stop_sprint(sheets_installed=12)

        original_end_time = sprint.end_time

        with self.assertRaisesMessage(
            ValidationError, "This boarding sprint has already stopped"
        ):
            sprint.stop_sprint(sheets_installed=20)

        sprint.refresh_from_db()

        self.assertEqual(sprint.end_time, original_end_time)
        self.assertEqual(sprint.sheets_installed, 12)

    def test_stop_sprint_rejects_negative_sheet_count(self):
        self._create_current_activity_log(self.boarding)
        sprint = BoardingSprint.objects.start_sprint()

        with self.assertRaises(ValidationError):
            sprint.stop_sprint(sheets_installed=-1)

        sprint.refresh_from_db()

        self.assertIsNone(sprint.end_time)
        self.assertIsNone(sprint.sheets_installed)
