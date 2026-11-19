BEGIN;

CREATE TABLE IF NOT EXISTS telemetry_batches (
    batch_id varchar(128) PRIMARY KEY,
    installation_hash char(64) NOT NULL,
    schema_version smallint NOT NULL,
    consent_version varchar(32) NOT NULL,
    received_at timestamptz NOT NULL DEFAULT now(),
    row_count integer NOT NULL CHECK (row_count > 0 AND row_count <= 500),
    payload_hash char(64) NOT NULL
);

CREATE TABLE IF NOT EXISTS usage_daily (
    day date NOT NULL,
    country_code char(2) NOT NULL,
    operating_system varchar(16) NOT NULL,
    provider varchar(64) NOT NULL,
    model varchar(128) NOT NULL,
    model_type varchar(16) NOT NULL CHECK (model_type IN ('model', 'model_family')),
    client_version varchar(64) NOT NULL,
    installation_hash char(64) NOT NULL,
    active_minutes bigint NOT NULL CHECK (active_minutes >= 0),
    api_call_count bigint NOT NULL CHECK (api_call_count >= 0),
    success_count bigint NOT NULL CHECK (success_count >= 0),
    error_count bigint NOT NULL CHECK (error_count >= 0),
    input_tokens bigint NOT NULL CHECK (input_tokens >= 0),
    output_tokens bigint NOT NULL CHECK (output_tokens >= 0),
    total_tokens bigint NOT NULL CHECK (total_tokens >= 0),
    PRIMARY KEY (
        day, country_code, operating_system, provider, model, model_type,
        client_version, installation_hash
    ),
    CHECK (success_count + error_count = api_call_count),
    CHECK (input_tokens + output_tokens = total_tokens)
);

CREATE INDEX IF NOT EXISTS usage_daily_day_idx ON usage_daily (day);
CREATE INDEX IF NOT EXISTS usage_daily_country_idx ON usage_daily (country_code);
CREATE INDEX IF NOT EXISTS usage_daily_provider_model_idx ON usage_daily (provider, model);
CREATE INDEX IF NOT EXISTS usage_daily_installation_idx ON usage_daily (installation_hash);

REVOKE ALL ON telemetry_batches, usage_daily FROM PUBLIC;

COMMIT;
