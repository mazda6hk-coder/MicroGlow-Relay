BEGIN;

ALTER TABLE usage_daily
    ADD COLUMN IF NOT EXISTS latency_lt_1s bigint NOT NULL DEFAULT 0 CHECK (latency_lt_1s >= 0),
    ADD COLUMN IF NOT EXISTS latency_1s_3s bigint NOT NULL DEFAULT 0 CHECK (latency_1s_3s >= 0),
    ADD COLUMN IF NOT EXISTS latency_3s_10s bigint NOT NULL DEFAULT 0 CHECK (latency_3s_10s >= 0),
    ADD COLUMN IF NOT EXISTS latency_gte_10s bigint NOT NULL DEFAULT 0 CHECK (latency_gte_10s >= 0),
    ADD COLUMN IF NOT EXISTS error_authentication bigint NOT NULL DEFAULT 0 CHECK (error_authentication >= 0),
    ADD COLUMN IF NOT EXISTS error_rate_limit bigint NOT NULL DEFAULT 0 CHECK (error_rate_limit >= 0),
    ADD COLUMN IF NOT EXISTS error_timeout bigint NOT NULL DEFAULT 0 CHECK (error_timeout >= 0),
    ADD COLUMN IF NOT EXISTS error_unavailable bigint NOT NULL DEFAULT 0 CHECK (error_unavailable >= 0),
    ADD COLUMN IF NOT EXISTS error_invalid_request bigint NOT NULL DEFAULT 0 CHECK (error_invalid_request >= 0),
    ADD COLUMN IF NOT EXISTS error_other bigint NOT NULL DEFAULT 0 CHECK (error_other >= 0),
    ADD COLUMN IF NOT EXISTS fallback_count bigint NOT NULL DEFAULT 0 CHECK (fallback_count >= 0);

COMMIT;

