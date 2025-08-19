CREATE OR REPLACE VIEW public.daily_durations AS
SELECT
    row_number() OVER () AS id,
    at2.date,
    sum(at2.duration) AS duration,
    a.name AS activity_name
FROM
    piecework_activitylog at2
    JOIN piecework_activity a ON a.id = at2.activity_id
WHERE
    at2.duration IS NOT NULL
GROUP BY
    at2.date,
    a.name;

COMMENT ON VIEW public.daily_durations IS 'total daily durations per activity';