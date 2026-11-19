"""Privacy-preserving telemetry for MicroGlow Relay.

Local consent, UTC daily aggregation, durable batches (MG-RELAY-003-A) plus the
production HTTP transport introduced by MG-RELAY-003-B.  Recording is always
non-blocking, and every failure stays silent and retryable.
"""

from .consent import CONSENT_VERSION_V1, CONSENT_VERSION_V2, TelemetryConsent
from .channel import classify_call_channel, load_official_hosts
from .endpoint import (
    TELEMETRY_ENDPOINT_URL,
    TELEMETRY_HOST,
    TELEMETRY_PATH,
    TELEMETRY_TIMEOUT_SECONDS,
)
from .runtime import TelemetryRuntime
from .store import (
    BATCH_STATES,
    TelemetryAggregator,
    TelemetryBatchStore,
    TelemetryUploadClient,
    UploadResponse,
)
from .transport import HttpTelemetryUploadClient
from .wiring import client_version, model_dimension, provider_key

__all__ = [
    "BATCH_STATES",
    "CONSENT_VERSION_V1",
    "CONSENT_VERSION_V2",
    "HttpTelemetryUploadClient",
    "TELEMETRY_ENDPOINT_URL",
    "TELEMETRY_HOST",
    "TELEMETRY_PATH",
    "TELEMETRY_TIMEOUT_SECONDS",
    "TelemetryAggregator",
    "TelemetryBatchStore",
    "TelemetryConsent",
    "TelemetryRuntime",
    "TelemetryUploadClient",
    "UploadResponse",
    "client_version",
    "classify_call_channel",
    "load_official_hosts",
    "model_dimension",
    "provider_key",
]
