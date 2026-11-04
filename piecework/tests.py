import datetime as dt
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import SimpleTestCase, TestCase
from django.urls import reverse
from numpy import number

from piecework.forms import UnitForm

from .models import (
    Activity,
    ActivityLog,
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
    def test_home_displays_active_unit_without_unit_selector(self):
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        response = self.client.get(reverse("piecework:home"))

        self.assertContains(response, f"Active unit: <strong>{active_unit}</strong>")
        admin_url = reverse(
            "admin:piecework_unit_change",
            kwargs={"object_id": active_unit.pk},
        )
        self.assertContains(
            response,
            f'href="{admin_url}"',
        )
        complete_url = reverse(
            "piecework:units_complete",
            kwargs={"pk": active_unit.pk},
        )
        self.assertContains(response, f'action="{complete_url}"')
        self.assertNotContains(response, 'name="unit_pk"')

    def test_mark_complete_updates_active_unit(self):
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)

        response = self.client.post(
            reverse(
                "piecework:units_complete",
                kwargs={"pk": active_unit.pk},
            )
        )

        self.assertRedirects(response, reverse("piecework:home"))
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

    def test_home_displays_message_and_disables_actions_without_active_unit(self):
        Activity.objects.create(name="board")

        response = self.client.get(reverse("piecework:home"))

        self.assertContains(response, "No active unit.")
        self.assertContains(response, "disabled")

    def test_start_activity_uses_active_unit(self):
        activity = Activity.objects.create(name="board")
        active_unit = Unit.objects.create(number="101", status=Unit.Status.ACTIVE)
        Unit.objects.create(number="102", status=Unit.Status.ON_HOLD)

        response = self.client.get(
            reverse("piecework:start-activity"),
            {"action": activity.name},
        )

        self.assertRedirects(response, reverse("piecework:home"))
        self.assertEqual(ActivityLog.objects.get().unit, active_unit)


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


class UnitViewTests(TestCase):
    def test_unit_delete_removes_unit(self):
        unit = Unit.objects.create(number="101")
        delete_url = reverse("piecework:units_delete", kwargs={"pk": unit.pk})

        response = self.client.post(delete_url)

        self.assertRedirects(response, reverse("piecework:units_index"))
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

    def test_units_create_displays_form(self):
        response = self.client.get(reverse("piecework:units_create"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "piecework/units/create.html")
        self.assertIsInstance(response.context["form"], UnitForm)

    def test_units_create_saves_valid_unit(self):
        response = self.client.post(
            reverse("piecework:units_create"),
            {
                "number": "101",
                "status": Unit.Status.ACTIVE,
                "height_feet": (HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE),
            },
        )

        self.assertRedirects(response, reverse("piecework:units_index"))
        self.assertTrue(Unit.objects.filter(number="101").exists())

    def test_units_detail_displays_unit(self):
        unit = Unit.objects.create(number="101")

        response = self.client.get(
            reverse("piecework:units_detail", kwargs={"pk": unit.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "piecework/units/detail.html")
        self.assertEqual(response.context["unit"], unit)
        self.assertContains(response, "Unit 101")

    def test_units_detail_returns_404_for_uknown_unit(self):
        response = self.client.get(
            reverse("piecework:units_detail", kwargs={"pk": 99999})
        )
        self.assertEqual(response.status_code, 404)

    def test_units_edit_display_form_for_unit(self):
        unit = Unit.objects.create(number="101")

        response = self.client.get(
            reverse("piecework:units_edit", kwargs={"pk": unit.pk})
        )

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "piecework/units/edit.html")
        self.assertEqual(response.context["form"].instance, unit)

    def test_units_updates_unit(self):
        unit = Unit.objects.create(
            number="101",
            status=Unit.Status.ON_HOLD,
        )

        response = self.client.post(
            reverse("piecework:units_edit", kwargs={"pk": unit.pk}),
            {
                "number": "102",
                "status": Unit.Status.ACTIVE,
                "height_feet": HeightCategory.OVER_EIGHT_TO_NINE_INCLUSIVE,
            },
        )

        unit.refresh_from_db()

        self.assertRedirects(
            response,
            reverse("piecework:units_detail", kwargs={"pk": unit.pk}),
        )
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
