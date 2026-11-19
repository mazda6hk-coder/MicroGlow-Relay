# Copyright (c) 2026 Zhengzhou Weiguang Intelligent Technology Center
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import date, timedelta
import hmac
import logging
from pathlib import Path
from typing import AsyncIterator

from fastapi import Depends, FastAPI, Header, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, RedirectResponse

from .config import Settings
from .geoip import GeoIPCountryResolver
from .network import TrustedSourceAddress
from .repository import BatchConflict, PostgresRepository, Repository
from .schemas import BatchAck, Health, TelemetryBatch
from .security import AnonymousRateLimiter, BodySizeLimitMiddleware


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
LOGGER = logging.getLogger("microglow.telemetry")
ADMIN_HTML = (Path(__file__).with_name("admin.html")).read_text(encoding="utf-8")
ADMIN_LOGO = Path(__file__).with_name("microglow-logo.png")
ADMIN_PAGE_HEADERS = {
    "Cache-Control": "no-store",
    "Content-Security-Policy": (
        "default-src 'none'; style-src 'unsafe-inline'; script-src 'unsafe-inline'; "
        "connect-src 'self'; img-src 'self' data:; base-uri 'none'; "
        "frame-ancestors 'none'; form-action 'none'"
    ),
    "Referrer-Policy": "no-referrer",
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
}


def _validation_error(_request: Request, error: RequestValidationError) -> JSONResponse:
    fields = [".".join(str(part) for part in item["loc"] if part != "body") for item in error.errors()]
    return JSONResponse({"error": "invalid_request", "fields": fields}, status_code=422)


def _lifespan(
    settings: Settings,
    supplied: Repository | None,
    supplied_geoip: GeoIPCountryResolver | None,
):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        repository = supplied or await PostgresRepository.connect(
            settings.database_url, settings.installation_hmac_secret
        )
        geoip = supplied_geoip or GeoIPCountryResolver(settings.geoip_database_path)
        app.state.repository = repository
        app.state.geoip = geoip
        try:
            yield
        finally:
            if supplied is None:
                await repository.close()
            if supplied_geoip is None:
                geoip.close()

    return lifespan


def _base_app(
    title: str,
    settings: Settings,
    repository: Repository | None,
    geoip: GeoIPCountryResolver | None = None,
) -> FastAPI:
    app = FastAPI(
        title=title,
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=_lifespan(settings, repository, geoip),
    )
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=settings.max_body_bytes)
    app.add_exception_handler(RequestValidationError, _validation_error)
    return app


def create_public_app(
    settings: Settings | None = None,
    repository: Repository | None = None,
    geoip: GeoIPCountryResolver | None = None,
) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    app = _base_app("MicroGlow Telemetry Collector", settings, repository, geoip)
    source_address = TrustedSourceAddress(settings.trusted_proxy_cidrs)
    limiter = AnonymousRateLimiter(
        settings.installation_hmac_secret,
        settings.public_rate_limit_per_minute,
        source_address,
    )

    @app.get("/health", response_model=Health)
    async def health(request: Request) -> Health:
        await request.app.state.repository.health()
        return Health()

    @app.post("/v1/telemetry/batches", response_model=BatchAck, dependencies=[Depends(limiter.allow)])
    async def telemetry_batch(batch: TelemetryBatch, request: Request) -> BatchAck:
        if len(batch.aggregated_rows) > settings.max_rows:
            raise HTTPException(status_code=422, detail="too_many_rows")
        expected_consent = (
            settings.consent_version_v1 if batch.schema_version == 1
            else settings.consent_version_v2
        )
        if not hmac.compare_digest(batch.consent_version, expected_consent):
            raise HTTPException(status_code=422, detail="consent_version_not_accepted")
        resolution = request.app.state.geoip.lookup(source_address.resolve(request))
        try:
            result = await request.app.state.repository.insert_batch(
                batch,
                resolution.country_code,
                resolution.country_source,
            )
        except BatchConflict as error:
            raise HTTPException(status_code=409, detail="batch_id_conflict") from error
        LOGGER.info("telemetry batch accepted rows=%d duplicate=%s", result.accepted_rows, result.duplicate)
        return BatchAck(
            batch_id=batch.batch_id,
            duplicate=result.duplicate,
            accepted_rows=result.accepted_rows,
        )

    return app


def create_admin_app(settings: Settings | None = None, repository: Repository | None = None) -> FastAPI:
    settings = settings or Settings.from_env()
    settings.validate()
    app = _base_app("MicroGlow Telemetry Admin", settings, repository)
    limiter = AnonymousRateLimiter(
        settings.installation_hmac_secret,
        settings.admin_rate_limit_per_minute,
        TrustedSourceAddress(settings.trusted_proxy_cidrs),
    )

    async def require_admin(
        request: Request,
        authorization: str | None = Header(default=None),
    ) -> None:
        await limiter.allow(request)
        expected = f"Bearer {settings.admin_token}"
        if authorization is None or not hmac.compare_digest(authorization, expected):
            raise HTTPException(status_code=401, detail="unauthorized", headers={"WWW-Authenticate": "Bearer"})

    @app.get("/admin", include_in_schema=False)
    async def admin_redirect() -> RedirectResponse:
        return RedirectResponse("/admin/", status_code=307)

    @app.get("/admin/", response_class=HTMLResponse, include_in_schema=False)
    async def admin_dashboard() -> HTMLResponse:
        return HTMLResponse(ADMIN_HTML, headers=ADMIN_PAGE_HEADERS)

    @app.get("/admin/assets/microglow-logo.png", include_in_schema=False)
    async def admin_logo() -> FileResponse:
        return FileResponse(
            ADMIN_LOGO,
            media_type="image/png",
            headers={"Cache-Control": "public, max-age=86400", "X-Content-Type-Options": "nosniff"},
        )

    @app.get("/admin/usage/summary", dependencies=[Depends(require_admin)])
    async def usage_summary(
        request: Request,
        from_day: date | None = Query(default=None),
        to_day: date | None = Query(default=None),
    ) -> dict:
        if from_day and to_day and from_day > to_day:
            raise HTTPException(status_code=422, detail="from_day_must_not_exceed_to_day")
        if from_day and to_day and to_day - from_day > timedelta(days=370):
            raise HTTPException(status_code=422, detail="date_range_may_not_exceed_370_days")
        return await request.app.state.repository.usage_summary(from_day, to_day)

    return app


public_app = create_public_app()
admin_app = create_admin_app()
