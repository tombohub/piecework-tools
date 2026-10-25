from django.db import migrations

DRYWALL_TYPE_MAP = {
    "regular": "regular",
    "dens glass": "dens_glass",
    "blue": "blue",
}


def map_sheet_counts_to_materials(apps, schema_editor):
    """
    Assign each existing UnitSheetCount to the corresponding
    DrywallMaterial using its legacy drywall type and length.
    """
    database = schema_editor.connection.alias

    UnitSheetCount = apps.get_model("piecework", "UnitSheetCount")
    DrywallMaterial = apps.get_model("piecework", "DrywallMaterial")

    sheet_counts = UnitSheetCount.objects.using(database).all().iterator()

    for sheet_count in sheet_counts:
        if sheet_count.drywall_type is None:
            raise RuntimeError(f"UnitSheetCount {sheet_count.pk} has no drywall type.")

        try:
            material_type = DRYWALL_TYPE_MAP[sheet_count.drywall_type]
        except KeyError:
            raise RuntimeError(
                f"Unknown drywall type {sheet_count.drywall_type!r} "
                f"on UnitSheetCount {sheet_count.pk}."
            ) from None

        try:
            material = DrywallMaterial.objects.using(database).get(
                drywall_type=material_type,
                length_feet=sheet_count.length,
            )
        except DrywallMaterial.DoesNotExist:
            raise RuntimeError(
                "No DrywallMaterial exists for "
                f"type={material_type!r}, length={sheet_count.length}, "
                f"required by UnitSheetCount {sheet_count.pk}."
            ) from None

        sheet_count.drywall_material = material
        sheet_count.save(update_fields=["drywall_material"])


def unmap_sheet_counts(apps, schema_editor):
    """
    Clear the DrywallMaterial foreign key when reversing this migration.

    The legacy drywall_type and length fields remain unchanged, so they can
    continue representing the material after the foreign key is cleared.
    """
    database = schema_editor.connection.alias
    UnitSheetCount = apps.get_model("piecework", "UnitSheetCount")

    UnitSheetCount.objects.using(database).update(
        drywall_material=None,
    )


class Migration(migrations.Migration):
    dependencies = [
        (
            "piecework",
            "0075_populate_drywall_materials",
        ),
    ]

    operations = [
        migrations.RunPython(
            map_sheet_counts_to_materials,
            unmap_sheet_counts,
        ),
    ]
