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

**Confirmado contra sandbox el 2026-04-24**: `GET /api/cuentas/{idCuenta}/posiciones` acepta `fecha` en formato `dd/mm/yyyy`. Sin excepciones.

**Formato de `fecha` en respuestas**: diferente por endpoint, **nunca ISO 8601**:

- `/posiciones` → `fecha` / `fechaPrecio` como `"dd/mm/yyyy"`.
- `/movimientos` → `fecha` como `"dd/mm/yyyy HH:MM:SS"`; `fechaDesde` / `fechaHasta` / `fechaConcertacion` como `"dd/mm/yyyy"` (o `null`).
- `/posicionValuada` → `fechaCotizacion` como `"dd/mm/yyyy"`; `fecha` llega como `null`.

Los modelos guardan estos strings verbatim. Si el caller necesita parsearlos a `datetime`, lo hace en su código — el cliente no hace parseo. No hay consistencia entre endpoints sobre qué fecha incluye hora, entonces no tiene sentido generalizar.

**Helper**: `format_date(value: date | None) -> str | None`

```python
from datetime import date
from higyrus_client._params import format_date

format_date(date(2026, 4, 23))       # "23/04/2026"
format_date(None)                      # None          (to be dropped)
```

**Strings no se aceptan**. Los wrappers públicos (`get_movimientos`, `get_posiciones`, `get_posicion_valuada`) tipan sus parámetros como `datetime.date`, no `str`. El cliente formatea siempre al wire format y el caller no puede pasar strings ya formateados — así evitamos que dos callers manden distinto shape al API (p. ej. uno con `"23/04/2026"`, otro con `"2026-04-23"`).

El cliente **no valida semánticamente** las fechas (p. ej. `fecha_desde > fecha_hasta` no se chequea). El API es la fuente de verdad y devuelve `400` si el rango es inválido.

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
