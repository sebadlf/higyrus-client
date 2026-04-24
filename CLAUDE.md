# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Python client library for the **Higyrus API** — REST API for financial operations (comprobantes, cuentas, posiciones, movimientos, contabilidad, unidades, operaciones). The library wraps REST endpoints into simple Python functions with automatic token management (Bearer / OAuth 2.0, 24h expiration).

## Development Commands

```bash
# Install dependencies (uses uv)
uv sync

# Run the example script
uv run python main.py

# Run the test suite
uv run pytest

# Run the type checker
uv run pyright

# Lint & format
uv run ruff check .
uv run ruff format .
```

Python 3.12+ is expected (pinned via `.python-version` once the package is bootstrapped).

## Architecture

_Pending bootstrap._ Planned structure:

- **`higyrus_client/`** — package with the client logic. Expected to follow the stateful-module pattern: module-level `_token`, `_session`, `_base_url` globals with `_ensure_token()` for auto-refresh before the 24h expiry. Auth:
  - **Bearer token** on `Authorization: Bearer <token>` header (OAuth 2.0 style), obtained via `POST /api/login`.
- **`higyrus_client/__init__.py`** — re-exports public functions as a flat namespace (`import higyrus_client as higyrus`).
- **`higyrus_client/exceptions.py`** — custom exceptions (`HigyrusAPIError`, `AuthenticationError`, etc.).

Document ADRs in `higyrus-vault/projects/higyrus-client/decisions/` as architectural choices are made.

## Configuration

Environment variables loaded from `.env` via `python-dotenv` (expected):
- `HIGYRUS_USER` — API username (required)
- `HIGYRUS_PASSWORD` — API password (required)
- `HIGYRUS_BASE_URL` — API base URL (required)

## API Reference

The full Higyrus API specification is in `documentation/higyrus-docs.pdf` (143 pages). Also available in PageIndex (`pi-cmoc427di0gw201nzwa1115it`) via the `pageindex` MCP server — use `get_document_structure` and `get_page_content` for targeted reads rather than loading the whole PDF.

Key concepts:
- Authentication via `POST /api/login` returns a Bearer token valid for 24h; only one active token per user (generating a new one invalidates the previous).
- Each endpoint requires specific permissions configured in the Higyrus platform; `403 Forbidden` indicates missing permission.
- Endpoint groups: `comprobantes`, `cuentas`, `personas`, `operaciones`, `contabilidad`, `unidades`, `health`.

## External References

- **Linear team**: `Becerra` (prefix `BEC`). Issues for this repo belong to the `Higyrus Client` project (https://linear.app/gravity-code/project/higyrus-client-4936c5ae7a62). Use the Linear MCP to read/create/update issues — always set `project` to `Higyrus Client` when creating issues for this repo, to keep them separate from `Matriz Client` and `AI Pipeline`.
- **Obsidian vault**: `./higyrus-vault/` — accessible via the `obsidian` MCP server. Contains:
  - `projects/higyrus-client/` — project-specific notes (domain, ADRs, runbooks)
  - `knowledge/` — cross-project knowledge (Python, architecture, tools)
  - `workflows/` — documented workflows
- **GitHub**: repo `sebadlf/higyrus-client`. Use the `github` MCP for PRs, issues, reviews.
- **PageIndex**: `documentation/higyrus-docs.pdf` already ingested — use the `pageindex` MCP server for API spec lookups.

## Git Conventions

- **Branch format**: `sebadlf-bec-{issue-number}-{short-description}` (copy from the Linear issue — it auto-generates this)
- **PR body**: must include the Linear issue ID (e.g., `BEC-7`) — triggers auto-link in Linear
- **Never commit directly to `main`** — protected branch, PR required
- **CI must pass** before merge: Ruff lint + format check, pytest, pyright (`.github/workflows/ci.yml`)

## Workflow

Para issues nuevos, el flujo es:

1. Leer el issue en Linear (via MCP) para entender el contexto.
2. Consultar notas relevantes del vault (`higyrus-vault/`, via obsidian MCP) — al menos `projects/higyrus-client/README.md`, ADRs, runbooks y domain notes que toquen el área.
3. Crear branch con el formato correcto.
4. Implementar, correr Ruff localmente (`uv run ruff check . && uv run ruff format .`).
5. Commitear y crear PR con link al issue de Linear.
6. Esperar CI verde y mergear (squash). Linear auto-cierra el issue.
7. **Cierre del ticket — actualizar el vault (paso obligatorio, no opcional).** Antes de pasar al próximo ticket, escribir lo que corresponda usando el `obsidian` MCP. Criterios:
   - **ADR** en `projects/higyrus-client/decisions/` — si introdujiste una decisión arquitectónica nueva, cambiaste una previa, o evaluaste alternativas que vale la pena recordar. Usar `_templates/tpl-adr.md` y numerar correlativo (`ADR-NNN`).
   - **Runbook** en `projects/higyrus-client/runbooks/` — si codificaste un procedimiento operativo que se va a repetir (release, rotación de credenciales, debugging de un endpoint problemático). Usar `_templates/tpl-runbook.md`.
   - **Domain note** en `projects/higyrus-client/domain/` — si descubriste un patrón del dominio (API, permisos, formatos de respuesta) que el código solo no comunica.
   - **Daily log** del día en `daily-logs/YYYY-MM-DD.md` — siempre, una entrada por ticket cerrado con qué se hizo, aprendizajes, y links a notas creadas/actualizadas. Crear el archivo con `_templates/tpl-daily-log.md` si todavía no existe para hoy.
   - **`projects/higyrus-client/README.md`** — actualizar si la nota nueva debería listarse en Decisiones, Runbooks o Notas de dominio.

   Si **ninguna** de las primeras tres aplica, igualmente registrar el ticket en el daily log con una línea que diga por qué no generó documentación nueva. Cero documentación silenciosa.
