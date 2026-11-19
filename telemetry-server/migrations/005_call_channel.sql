BEGIN;
ALTER TABLE usage_daily ADD COLUMN IF NOT EXISTS call_channel varchar(16) NOT NULL DEFAULT 'unknown';
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_constraint WHERE conrelid = 'usage_daily'::regclass AND conname = 'usage_daily_call_channel_check') THEN
        ALTER TABLE usage_daily ADD CONSTRAINT usage_daily_call_channel_check
            CHECK (call_channel IN ('official', 'relay', 'unknown'));
    END IF;
END $$;
DROP INDEX IF EXISTS usage_daily_dimensions_key;
CREATE UNIQUE INDEX usage_daily_dimensions_key ON usage_daily (
    day, country_code, country_source, operating_system, provider, model,
    model_type, client_version, installation_hash, call_channel
) NULLS NOT DISTINCT;
COMMIT;
