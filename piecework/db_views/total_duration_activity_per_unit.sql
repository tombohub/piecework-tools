-- public.total_duration_activity_per_unit source

CREATE OR REPLACE VIEW public.total_duration_activity_per_unit AS
SELECT piecework_unit.number, piecework_activity.name AS activity, sum(
        piecework_activitylog.duration
    ) AS duration
FROM
    piecework_activitylog
    JOIN piecework_activity ON piecework_activity.id = piecework_activitylog.activity_id
    JOIN piecework_unit ON piecework_unit.id = piecework_activitylog.unit_id
GROUP BY
    piecework_unit.number,
    piecework_activity.name
ORDER BY piecework_unit.number;

COMMENT ON VIEW public.total_duration_activity_per_unit IS 'Total duration of each actvity per unit';