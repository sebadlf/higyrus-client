---
tags: [domain, higyrus-client, api]
---

# Convenciones de query params de la API de Higyrus

La API de Higyrus usa convenciones consistentes para query string que no son las default de `requests`. Esta nota documenta las tres que aparecen repetidas en el PDF y cómo las resolvemos en el cliente (`higyrus_client/_params.py`).

## Fechas

**Formato del wire**: `dd/mm/yyyy` (no ISO `yyyy-mm-dd`).

Aparece en:

- `GET /api/cuentas/{idCuenta}/movimientos` → `fechaDesde`, `fechaHasta`
- `GET /api/cuentas/movimientos` → `fechaDesde`, `fechaHasta`
- `GET /api/cuentas/{idCuenta}/posicionValuada` → `desde`, `hasta`
- `GET /api/cuentas/{idCuenta}/informeAuditoriaDetalle` → `desde`, `hasta`
- `GET /api/contabilidad/registrosContables` → `fechaDesde`, `fechaHasta`
- `GET /api/contabilidad/registrosContablesResumenDiario` → `fechaDesde`, `fechaHasta`
- `GET /api/cuentas/saldos/consolidados` → rangos de fechas

**Excepción pendiente de validar**: `GET /api/cuentas/{idCuenta}/posiciones` pide una `fecha` pero el PDF no especifica el formato. Hasta que se pruebe contra sandbox, asumimos `dd/mm/yyyy` por consistencia. Actualizar esta nota y el ticket BEC-78 cuando se confirme.

**Helper**: `format_date(value: date | datetime | str | None) -> str | None`

```python
from datetime import date
from higyrus_client._params import format_date

format_date(date(2026, 4, 23))       # "23/04/2026"
format_date("23/04/2026")             # "23/04/2026"  (passthrough)
format_date(None)                      # None          (to be dropped)
```

**No validamos client-side**. Si alguien pasa `"not a date"`, la call sale con ese string y el API devuelve 400. Duplicar la validación acá solo agrega un punto de falla sin valor.

## Booleans

**Formato del wire**: string capitalizado `"True"` / `"False"` (igual que `str(bool)` de Python), **no** `"true"` / `"false"` lowercase JavaScript-style.

Aparece en:

- `GET /api/cuentas/{idCuenta}/posiciones` → `incluirParking`
- `GET /api/cuentas/{idCuenta}/posicionValuada` → `ocultarCerradas`, `concertacion`, `actualizar`
- `GET /api/cuentas/{idCuenta}/informeAuditoriaDetalle` → `concertacion`, `soloCP`
- `GET /api/operaciones/consolidadosGenerales` → `soloAccesorios`, `ocultarContabilidad`, `ocultarSaldosEnCero`
- `GET /api/cuentas/saldos/consolidados` → `excluirSaldosIniciales`, `ocultarContabilidad`, `ocultarSaldosEnCero`
- `GET /api/contabilidad/registrosContables` → `inclNC`
- Varios más en el PDF

**Helper**: `format_bool(value: bool | None) -> str | None`

```python
from higyrus_client._params import format_bool

format_bool(True)    # "True"
format_bool(False)   # "False"
format_bool(None)    # None  (to be dropped)
```

## Arrays complejos

Algunos endpoints aceptan arrays estructurados URL-encoded como query param. El caso más complejo es `gruposCuentas` en `GET /api/operaciones/consolidadosGenerales`, que admite 9 tipos de grupo (Cartera, Categoria, Grupo, Administrador, Operador, Sucursal, Tipo de cuenta, Clase de cuenta, Titular) con semántica propia (pp. 65-67 del PDF).

**No está cubierto por los helpers de este módulo todavía** — lo vamos a implementar en el ticket que consuma `/api/operaciones/consolidadosGenerales` (pendiente de crear). La nota queda acá para no perder la referencia.

## Drop de `None`

Cuando un wrapper público recibe kwargs en snake_case, algunos van a ser `None` (por los defaults). Esos no deben viajar al API — la convención es **dropearlos del query string**.

**Helper**: `drop_none(params: dict[str, Any]) -> dict[str, Any]`

Preserva explícitamente `False`, `0` y `""` porque son inputs válidos (p. ej. `incluirParking=False`).

El helper es llamado por `_request` dentro de `client.py`, así que los wrappers públicos solo tienen que poner `None` para campos no especificados y dejar que el transporte los limpie.

## snake_case en Python ↔ camelCase en wire

El cliente expone funciones con kwargs en **snake_case** (Python-idiomático):

```python
higyrus.get_posiciones(id_cuenta="123", fecha=date(2026, 4, 23), incluir_parking=False)
```

Y el wrapper las traduce **explícitamente** al camelCase del wire antes de pasarlas al request:

```python
params = {
    "fecha": format_date(fecha),
    "especie": especie,
    "incluirParking": format_bool(incluir_parking),
}
return _get(f"/api/cuentas/{id_cuenta}/posiciones", **params)
```

**¿Por qué no convertir automáticamente?** La traducción automática (`snake_case → camelCase`) funciona el 95% del tiempo pero los edge cases cuestan caro: params como `CUIT` (todo mayúsculas) o `idComprobante` rompen la convención; el auto-map hace ruido silencioso que aparece como 400 en producción sin pistas. La traducción explícita es 3 líneas más por endpoint y vale la pena.

## Referencias

- Implementación: `higyrus_client/_params.py`
- Tests: `tests/test_params.py`
- Ticket: [BEC-81](https://linear.app/gravity-code/issue/BEC-81/foundation-helpers-de-parametros-de-query-fechas-bools-arrays)
