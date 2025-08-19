CREATE OR REPLACE VIEW public.completed_units_square_footage AS
SELECT piecework_unit.number AS unit_number, sum(
        piecework_unitsheetcount.length * 4 * piecework_unitsheetcount.count
    ) AS footage
FROM
    piecework_unitsheetcount
    JOIN piecework_unit ON piecework_unit.id = piecework_unitsheetcount.unit_id
GROUP BY
    piecework_unit.number;

COMMENT ON VIEW public.completed_units_square_footage IS 'Square footage for each completed unit. Only after unit completion we know exactly how much drywall is used.';