BEGIN;

ALTER TABLE usage_daily
    ADD COLUMN IF NOT EXISTS country_source varchar(32);

ALTER TABLE usage_daily DROP CONSTRAINT IF EXISTS usage_daily_pkey;
ALTER TABLE usage_daily ALTER COLUMN country_code DROP NOT NULL;

-- Historical values came from the client and cannot be represented as GEOIP.
-- Collapse any dimensions that become equal after removing the untrusted country,
-- preserving every aggregate without inventing a country.
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM usage_daily WHERE country_source IS NULL) THEN
        CREATE TEMP TABLE usage_daily_geoip_migration ON COMMIT DROP AS
        SELECT day,
               CASE WHEN country_source IS NULL THEN NULL ELSE country_code END AS country_code,
               COALESCE(country_source, 'COUNTRY-SOURCE-GAP') AS country_source,
               operating_system, provider, model, model_type, client_version, installation_hash,
               SUM(active_minutes)::bigint AS active_minutes,
               SUM(api_call_count)::bigint AS api_call_count,
               SUM(success_count)::bigint AS success_count,
               SUM(error_count)::bigint AS error_count,
               SUM(input_tokens)::bigint AS input_tokens,
               SUM(output_tokens)::bigint AS output_tokens,
               SUM(total_tokens)::bigint AS total_tokens,
               SUM(latency_lt_1s)::bigint AS latency_lt_1s,
               SUM(latency_1s_3s)::bigint AS latency_1s_3s,
               SUM(latency_3s_10s)::bigint AS latency_3s_10s,
               SUM(latency_gte_10s)::bigint AS latency_gte_10s,
               SUM(error_authentication)::bigint AS error_authentication,
               SUM(error_rate_limit)::bigint AS error_rate_limit,
               SUM(error_timeout)::bigint AS error_timeout,
               SUM(error_unavailable)::bigint AS error_unavailable,
               SUM(error_invalid_request)::bigint AS error_invalid_request,
               SUM(error_other)::bigint AS error_other,
               SUM(fallback_count)::bigint AS fallback_count
        FROM usage_daily
        GROUP BY day,
                 CASE WHEN country_source IS NULL THEN NULL ELSE country_code END,
                 COALESCE(country_source, 'COUNTRY-SOURCE-GAP'),
                 operating_system, provider, model, model_type, client_version, installation_hash;

        TRUNCATE usage_daily;
        INSERT INTO usage_daily (
            day, country_code, country_source, operating_system, provider, model, model_type,
            client_version, installation_hash, active_minutes, api_call_count, success_count,
            error_count, input_tokens, output_tokens, total_tokens, latency_lt_1s,
            latency_1s_3s, latency_3s_10s, latency_gte_10s, error_authentication,
            error_rate_limit, error_timeout, error_unavailable, error_invalid_request,
            error_other, fallback_count
        ) SELECT * FROM usage_daily_geoip_migration;
    END IF;
END $$;

ALTER TABLE usage_daily ALTER COLUMN country_source SET NOT NULL;
ALTER TABLE usage_daily ALTER COLUMN country_source SET DEFAULT 'COUNTRY-SOURCE-GAP';

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'usage_daily_country_source_check'
    ) THEN
        ALTER TABLE usage_daily ADD CONSTRAINT usage_daily_country_source_check CHECK (
            (country_source = 'GEOIP' AND country_code IS NOT NULL)
            OR (country_source = 'COUNTRY-SOURCE-GAP' AND country_code IS NULL)
        );
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM pg_constraint WHERE conname = 'usage_daily_country_iso_check'
    ) THEN
        ALTER TABLE usage_daily ADD CONSTRAINT usage_daily_country_iso_check CHECK (
            country_code IS NULL OR btrim(country_code) = ANY (ARRAY[
                'AD','AE','AF','AG','AI','AL','AM','AO','AQ','AR','AS','AT','AU','AW','AX','AZ',
                'BA','BB','BD','BE','BF','BG','BH','BI','BJ','BL','BM','BN','BO','BQ','BR','BS',
                'BT','BV','BW','BY','BZ','CA','CC','CD','CF','CG','CH','CI','CK','CL','CM','CN',
                'CO','CR','CU','CV','CW','CX','CY','CZ','DE','DJ','DK','DM','DO','DZ','EC','EE',
                'EG','EH','ER','ES','ET','FI','FJ','FK','FM','FO','FR','GA','GB','GD','GE','GF',
                'GG','GH','GI','GL','GM','GN','GP','GQ','GR','GS','GT','GU','GW','GY','HK','HM',
                'HN','HR','HT','HU','ID','IE','IL','IM','IN','IO','IQ','IR','IS','IT','JE','JM',
                'JO','JP','KE','KG','KH','KI','KM','KN','KP','KR','KW','KY','KZ','LA','LB','LC',
                'LI','LK','LR','LS','LT','LU','LV','LY','MA','MC','MD','ME','MF','MG','MH','MK',
                'ML','MM','MN','MO','MP','MQ','MR','MS','MT','MU','MV','MW','MX','MY','MZ','NA',
                'NC','NE','NF','NG','NI','NL','NO','NP','NR','NU','NZ','OM','PA','PE','PF','PG',
                'PH','PK','PL','PM','PN','PR','PS','PT','PW','PY','QA','RE','RO','RS','RU','RW',
                'SA','SB','SC','SD','SE','SG','SH','SI','SJ','SK','SL','SM','SN','SO','SR','SS',
                'ST','SV','SX','SY','SZ','TC','TD','TF','TG','TH','TJ','TK','TL','TM','TN','TO',
                'TR','TT','TV','TW','TZ','UA','UG','UM','US','UY','UZ','VA','VC','VE','VG','VI',
                'VN','VU','WF','WS','YE','YT','ZA','ZM','ZW'
            ]::text[])
        );
    END IF;
END $$;

CREATE UNIQUE INDEX IF NOT EXISTS usage_daily_dimensions_key
    ON usage_daily (
        day, country_code, country_source, operating_system, provider, model,
        model_type, client_version, installation_hash
    ) NULLS NOT DISTINCT;

CREATE INDEX IF NOT EXISTS usage_daily_country_source_idx
    ON usage_daily (country_source);

COMMIT;
