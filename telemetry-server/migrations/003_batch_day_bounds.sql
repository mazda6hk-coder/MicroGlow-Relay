BEGIN;

ALTER TABLE telemetry_batches
    ADD COLUMN IF NOT EXISTS aggregation_day_min date,
    ADD COLUMN IF NOT EXISTS aggregation_day_max date;

CREATE INDEX IF NOT EXISTS telemetry_batches_day_bounds_idx
    ON telemetry_batches (aggregation_day_min, aggregation_day_max);

COMMIT;

