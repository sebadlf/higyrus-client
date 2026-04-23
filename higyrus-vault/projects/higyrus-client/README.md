---
tags: [project, fintech]
status: active
repo: github.com/sebadlf/higyrus-client
---

# Higyrus Client

Cliente Python para la **API de Higyrus** — API REST para operaciones financieras (comprobantes, cuentas, posiciones, movimientos, contabilidad, unidades, operaciones). Autenticación vía token Bearer (OAuth 2.0) con expiración de 24 horas.

## Links

- Repo: `github.com/sebadlf/higyrus-client` (local: `~/development/becerra/higyrus-client`)
- API spec: `documentation/higyrus-docs.pdf` en el repo (también disponible en PageIndex)
- Linear team: `Becerra` (prefix `BEC`) — https://linear.app/gravity-code/team/BEC
- Branch format: `sebadlf-bec-{n}-{descripcion}`
- Distribución: GitHub Releases (no PyPI), workflow `release.yml` por tag `v*`

## Estado actual

- Proyecto recién iniciado — pendiente bootstrap del paquete Python.
- Toolchain planeado: `uv`, `ruff` (lint + format), `pyright` (standard), `pytest`.
- CI: lint + format + tests + pyright en cada PR.
- Dependencias previstas: `requests`, `python-dotenv`.

## Decisiones

_Pendientes. Al tomar una decisión arquitectónica, registrar en `decisions/` usando el template `tpl-adr`._

## Notas de dominio

_Pendientes. Al descubrir patrones del dominio (API, permisos, formatos), registrar en `domain/`._

## Runbooks

_Pendientes. Al codificar procedimientos operativos (setup, release, rotación de credenciales), registrar en `runbooks/`._
