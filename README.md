# higyrus-client

Python client for the **Higyrus API** — REST API for financial operations (comprobantes, cuentas, posiciones, movimientos, contabilidad, unidades, operaciones). The library wraps REST endpoints into simple Python functions with automatic Bearer token management (24 h expiry).

Requires Python 3.12+.

## Installation

Clone and install from source:

```bash
git clone https://github.com/sebadlf/higyrus-client.git
cd higyrus-client
uv sync
```

## Configuration

The client loads credentials from environment variables (or a `.env` file via `python-dotenv`):

| Variable | Description |
|---|---|
| `HIGYRUS_USER` | API username (required) |
| `HIGYRUS_PASSWORD` | API password (required) |
| `HIGYRUS_BASE_URL` | Base URL up to the `/api` prefix (required). E.g. `https://cliente.aunesa.com/Irmo` |
| `HIGYRUS_CLIENT_ID` | Tenant / client identifier (optional; sent as `""` when unset) |

## Quickstart

```python
import higyrus_client as higyrus

# No auth required
status = higyrus.get_health()
print(status)

# Bearer token obtained via POST /api/login, cached for 24 h
higyrus.login()
```

The token is refreshed automatically one hour before its 24 h expiry on any subsequent API call, so callers usually do not need to invoke `login()` explicitly.

## Development

```bash
uv sync
uv run ruff check .
uv run ruff format --check .
uv run pyright
uv run pytest
```

## Reference

- Full Higyrus API documentation: [`documentation/higyrus-docs.pdf`](./documentation/higyrus-docs.pdf)
- Public surface: `higyrus_client.__all__`

## Releases

Distribution happens via GitHub Releases (no PyPI). The [`release.yml`](.github/workflows/release.yml) workflow builds and publishes a wheel + sdist on every `v*` tag push.

Cutting a new release:

1. Bump `project.version` in `pyproject.toml`.
2. Commit and merge the bump to `main`.
3. Tag the commit: `git tag v0.1.0 && git push origin v0.1.0`.
4. The workflow validates that the tag matches the version, builds the artifacts, and uploads them to the corresponding Release.

## License

MIT © Sebastián de la Fuente
