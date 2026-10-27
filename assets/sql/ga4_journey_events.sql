-- Pixelkiez GA4 BigQuery journey export helper.
-- Replace PROJECT.DATASET and date suffixes at runtime. Do not embed credentials.
-- This query emits only fields required by the downstream journey aggregator.
SELECT
  user_pseudo_id,
  event_timestamp,
  event_name,
  (SELECT value.string_value FROM UNNEST(event_params) WHERE key = 'page_location') AS page_location
FROM `PROJECT.DATASET.events_*`
WHERE _TABLE_SUFFIX BETWEEN 'START_YYYYMMDD' AND 'END_YYYYMMDD'
  AND event_name IN ('page_view', 'primary_cta_click', 'form_start', 'form_submit', 'phone_click', 'booking_start', 'booking_complete')
ORDER BY user_pseudo_id, event_timestamp;
