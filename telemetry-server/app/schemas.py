from __future__ import annotations

from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


ISO_ALPHA2 = frozenset(
    "AD AE AF AG AI AL AM AO AQ AR AS AT AU AW AX AZ BA BB BD BE BF BG BH BI BJ BL BM BN BO BQ BR BS BT BV BW BY BZ CA CC CD CF CG CH CI CK CL CM CN CO CR CU CV CW CX CY CZ DE DJ DK DM DO DZ EC EE EG EH ER ES ET FI FJ FK FM FO FR GA GB GD GE GF GG GH GI GL GM GN GP GQ GR GS GT GU GW GY HK HM HN HR HT HU ID IE IL IM IN IO IQ IR IS IT JE JM JO JP KE KG KH KI KM KN KP KR KW KY KZ LA LB LC LI LK LR LS LT LU LV LY MA MC MD ME MF MG MH MK ML MM MN MO MP MQ MR MS MT MU MV MW MX MY MZ NA NC NE NF NG NI NL NO NP NR NU NZ OM PA PE PF PG PH PK PL PM PN PR PS PT PW PY QA RE RO RS RU RW SA SB SC SD SE SG SH SI SJ SK SL SM SN SO SR SS ST SV SX SY SZ TC TD TF TG TH TJ TK TL TM TN TO TR TT TV TW TZ UA UG UM US UY UZ VA VC VE VG VI VN VU WF WS YE YT ZA ZM ZW".split()
)


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class LatencyBuckets(StrictModel):
    lt_1s: int = Field(ge=0, le=1_000_000_000)
    from_1s_to_3s: int = Field(ge=0, le=1_000_000_000)
    from_3s_to_10s: int = Field(ge=0, le=1_000_000_000)
    gte_10s: int = Field(ge=0, le=1_000_000_000)

    @property
    def total(self) -> int:
        return self.lt_1s + self.from_1s_to_3s + self.from_3s_to_10s + self.gte_10s


class ErrorCategoryCounts(StrictModel):
    authentication: int = Field(ge=0, le=1_000_000_000)
    rate_limit: int = Field(ge=0, le=1_000_000_000)
    timeout: int = Field(ge=0, le=1_000_000_000)
    unavailable: int = Field(ge=0, le=1_000_000_000)
    invalid_request: int = Field(ge=0, le=1_000_000_000)
    other: int = Field(ge=0, le=1_000_000_000)

    @property
    def total(self) -> int:
        return (
            self.authentication + self.rate_limit + self.timeout
            + self.unavailable + self.invalid_request + self.other
        )


class AggregatedRow(StrictModel):
    call_channel: Literal["official", "relay", "unknown"] = "unknown"
    # Legacy clients may still send this field, but server-side GeoIP is the
    # only country source. New clients omit it entirely.
    country_code: str | None = Field(default=None, min_length=2, max_length=2)
    client_version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")
    # Legacy sealed batches can still supply this; new clients omit it.
    operating_system: Literal["windows", "macos", "linux", "other"] | None = None
    provider: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
    model: str | None = Field(default=None, min_length=1, max_length=128)
    model_family: str | None = Field(default=None, min_length=1, max_length=128)
    active_minutes: int = Field(ge=0, le=1_440)
    api_call_count: int = Field(ge=0, le=1_000_000_000)
    success_count: int = Field(ge=0, le=1_000_000_000)
    error_count: int = Field(ge=0, le=1_000_000_000)
    input_tokens: int = Field(ge=0, le=1_000_000_000_000)
    output_tokens: int = Field(ge=0, le=1_000_000_000_000)
    total_tokens: int = Field(ge=0, le=2_000_000_000_000)
    aggregation_day: date
    latency_buckets: LatencyBuckets | None = None
    error_category_counts: ErrorCategoryCounts | None = None
    fallback_count: int | None = Field(default=None, ge=0, le=1_000_000_000)

    @field_validator("country_code")
    @classmethod
    def validate_country(cls, value: str | None) -> str | None:
        if value is not None and value not in ISO_ALPHA2:
            raise ValueError("must be an uppercase ISO 3166-1 alpha-2 country code")
        return value

    @field_validator("model", "model_family")
    @classmethod
    def reject_control_characters(cls, value: str | None) -> str | None:
        if value is not None and any(ord(character) < 32 for character in value):
            raise ValueError("control characters are not allowed")
        return value

    @field_validator("aggregation_day")
    @classmethod
    def validate_day(cls, value: date) -> date:
        current = datetime.now(timezone.utc).date()
        # A client near the date line can be one calendar day ahead of the
        # server's UTC-local date while still reporting its legitimate day.
        if value > current + timedelta(days=1) or value < current - timedelta(days=370):
            raise ValueError("aggregation_day must be within the accepted 370-day window")
        return value

    @field_validator("aggregation_day", mode="before")
    @classmethod
    def parse_iso_day(cls, value: object) -> object:
        if isinstance(value, str):
            try:
                return date.fromisoformat(value)
            except ValueError as error:
                raise ValueError("aggregation_day must be an ISO date") from error
        return value

    @model_validator(mode="after")
    def validate_totals(self) -> "AggregatedRow":
        if (self.model is None) == (self.model_family is None):
            raise ValueError("exactly one of model or model_family is required")
        if self.success_count + self.error_count != self.api_call_count:
            raise ValueError("success_count + error_count must equal api_call_count")
        if self.input_tokens + self.output_tokens != self.total_tokens:
            raise ValueError("input_tokens + output_tokens must equal total_tokens")
        if self.latency_buckets is not None and self.latency_buckets.total != self.api_call_count:
            raise ValueError("latency bucket counts must equal api_call_count")
        if self.error_category_counts is not None and self.error_category_counts.total != self.error_count:
            raise ValueError("error category counts must equal error_count")
        if self.fallback_count is not None and self.fallback_count > self.api_call_count:
            raise ValueError("fallback_count may not exceed api_call_count")
        return self

    @property
    def normalized_model(self) -> str:
        return self.model if self.model is not None else self.model_family or ""

    @property
    def model_type(self) -> str:
        return "model" if self.model is not None else "model_family"


class TelemetryBatch(StrictModel):
    schema_version: Literal[1, 2]
    batch_id: str = Field(min_length=16, max_length=128, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:\-]*$")
    installation_id: str = Field(min_length=16, max_length=256, pattern=r"^[A-Za-z0-9][A-Za-z0-9._:\-]*$")
    consent_version: str = Field(min_length=1, max_length=32, pattern=r"^[A-Za-z0-9][A-Za-z0-9._\-]*$")
    consent: Literal[True]
    client_version: str = Field(min_length=1, max_length=64, pattern=r"^[A-Za-z0-9][A-Za-z0-9._+\-]*$")
    aggregated_rows: list[AggregatedRow] = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def consistent_client_version(self) -> "TelemetryBatch":
        if any(row.client_version != self.client_version for row in self.aggregated_rows):
            raise ValueError("row client_version must match batch client_version")
        quality_fields = (
            (row.latency_buckets, row.error_category_counts, row.fallback_count)
            for row in self.aggregated_rows
        )
        if self.schema_version == 1:
            if any(any(value is not None for value in fields) for fields in quality_fields):
                raise ValueError("quality aggregates require schema_version 2")
        else:
            if not self.consent_version.startswith("v2"):
                raise ValueError("schema_version 2 requires a v2 consent_version")
            if any(any(value is None for value in fields) for fields in quality_fields):
                raise ValueError("schema_version 2 requires all quality aggregate fields")
        return self


class BatchAck(StrictModel):
    ack: Literal[True] = True
    batch_id: str
    duplicate: bool
    accepted_rows: int


class Health(StrictModel):
    status: Literal["ok"] = "ok"
