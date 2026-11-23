# Third-party notices

MicroGlow Relay includes or depends on the third-party components listed below.
Each component remains under its own license. Full license texts are stored in
[`docs/licenses/`](licenses/).

## Runtime dependencies (Windows application)

| Component | Version | License | Full text |
|---|---|---|---|
| PySide6 / shiboken6 (Qt for Python) | 6.11.2 | LGPL-3.0 (alternatively GPL-3.0 or commercial) | `docs/licenses/Qt-LGPL-3.0.txt`, `docs/licenses/Qt-GPL-3.0.txt` |
| httpx | 0.28.1 | BSD-3-Clause | `docs/licenses/httpx-0.28.1.dist-info-LICENSE.md` |
| tomli/tomlkit | 0.15.1 | MIT | `docs/licenses/tomlkit-0.15.1.dist-info-LICENSE` |
| httpcore | 1.0.9 | BSD-3-Clause | `docs/licenses/httpcore-1.0.9.dist-info-LICENSE.md` |
| h11 | 0.16.0 | MIT | `docs/licenses/h11-0.16.0.dist-info-LICENSE.txt` |
| anyio | 4.15.1 | MIT | `docs/licenses/anyio-4.15.1.dist-info-LICENSE` |
| certifi | 2026.7.22 | MPL-2.0 | `docs/licenses/certifi-2026.7.22.dist-info-LICENSE` |
| idna | 3.20 | BSD-3-Clause | `docs/licenses/idna-3.20.dist-info-LICENSE.md` |
| typing_extensions | 4.16.0 | PSF-2.0 | `docs/licenses/typing_extensions-4.16.0.dist-info-LICENSE` |

Python itself is distributed under the Python Software Foundation License:
`docs/licenses/Python-LICENSE.txt`.

## Build-time dependencies (not distributed)

| Component | Version | License | Notes |
|---|---|---|---|
| PyInstaller | 6.22.3 | GPL-2.0-or-later with a special exception for bootloaders | Used to build the Windows executable; not imported by the application at runtime. `docs/licenses/pyinstaller-6.22.3.dist-info-COPYING.txt` |
| Pillow | 12.3.0 | MIT-CMU (HPND) | Used by `tools/make_icon.py` to generate the application icon at build time. |

## Telemetry ingestion service (`telemetry-server/`)

| Component | Version | License |
|---|---|---|
| FastAPI | 0.116.1 | MIT |
| Uvicorn | 0.35.0 | BSD-3-Clause |
| Pydantic | 2.11.7 | MIT |
| asyncpg | 0.30.0 | Apache-2.0 |
| maxminddb | 2.8.2 | Apache-2.0 |
| PostgreSQL | 16 | PostgreSQL License (used as a service, not bundled) |
| DB-IP Lite IP-to-Country | monthly snapshot | CC BY 4.0 — "IP geolocation data by DB-IP.com" (server-side only; not bundled with the client) |

See `telemetry-server/DBIP_ATTRIBUTION.md` for the DB-IP attribution details.

## Fonts

| Font | License | Location |
|---|---|---|
| Source Sans 3 | SIL Open Font License 1.1 | `assets/fonts/source-sans-3/LICENSE-OFL.txt` |

The application requests "Source Sans 3" for the odometer display and falls back
to system fonts. The bundled font file is distributed under the OFL; the
reserved font name "Source" may not be used for modified versions.

## Icons and brand marks

| Asset | License | Notes |
|---|---|---|
| Lucide icons | ISC | `docs/licenses/Lucide-ISC.txt` |
| Simple Icons (model brand marks) | CC0-1.0 | `docs/licenses/SimpleIcons-CC0.txt` |
| LobeHub assets | MIT | `docs/licenses/LobeHub-MIT.txt` |

Third-party product names and logos are trademarks of their respective owners
and are used only to identify the corresponding services. See `TRADEMARKS.md`.

## Qt / PySide6 and LGPL-3.0

MicroGlow Relay is built with PySide6, which is available under LGPL-3.0 (or
GPL-3.0, or a commercial Qt license). This project relies on the LGPL-3.0
option. LGPL-3.0 requires that recipients be able to replace or relink the LGPL
components.

The current Windows build packages the application and Qt libraries into a
single executable with PyInstaller **onefile**. Whether this packaging fully
satisfies the LGPL-3.0 replacement requirement has **not been confirmed**.
Possible resolutions, to be decided before a signed commercial release:

1. distribute an **onedir** build that keeps the Qt DLLs as separate,
   replaceable files;
2. provide the relinkable object files or a documented rebuild path together
   with the binary;
3. obtain a commercial Qt license.

The full source and build scripts are published in this repository, so anyone
can rebuild the application with modified Qt libraries. Qt's LGPL text is
included at `docs/licenses/Qt-LGPL-3.0.txt`.
