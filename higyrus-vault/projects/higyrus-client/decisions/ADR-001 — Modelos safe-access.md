---
date: 2026-04-23
status: accepted
tags: [adr, models, higyrus-client]
---

# ADR-001: Modelos safe-access (frozen dataclasses) sobre dict/Pydantic

## Contexto

La API de Higyrus devuelve respuestas JSON con muchas keys condicionales. Ejemplos de la documentación (`documentation/higyrus-docs.pdf`):

- En `/api/cuentas/{idCuenta}/posiciones`, el campo `disponibleAjustado` **solo** aparece para instrumentos FCI cuando el parámetro de plataforma `irmo.fci.rescate_estadoSolicitudesAdescontar` está activado. En cualquier otro caso, la key ni siquiera viene en el payload.
- El array `parking` dentro de cada `Posicion` puede no venir si la cuenta no tiene operaciones en parking.
- Los endpoints de detalle (p.ej. `/api/cuentas/{idCuenta}`) devuelven estructuras muy anidadas (cuenta → personas → domicilios → comunicaciones) donde cualquier nivel puede estar vacío o ausente.

Si el cliente expone las respuestas como `dict[str, Any]` o como `dataclass` estándar, todo acceso chaineado (`posicion.parking[0].diasParking`, `cuenta.personas[0].domicilio.calle`) es una mina: el primer `KeyError` / `AttributeError` lo tenés en producción, no en tests.

Queremos una representación tipada que:

1. Garantice que el acceso chaineado nunca rompa, incluso con payloads parciales.
2. No agregue dependencias pesadas.
3. Sea ergonómica para el usuario del cliente (`import higyrus_client as higyrus; higyrus.get_posiciones(...)`).
4. Sea fácil de testear y de refactorizar.

## Decisión

**Frozen dataclasses con `from_api(payload)` y defaults seguros por tipo**, todos los modelos heredando de `SafeModel` (base en `higyrus_client/models.py`).

Resumen del patrón:

```python
@dataclass(frozen=True, slots=True)
class Posicion(SafeModel):
    cuenta: str
    disponibleAjustado: float
    parking: list[Parking]
    # ... todos los campos del wire format en camelCase
```

`SafeModel.from_api(payload)` inspecciona `get_type_hints(cls)` y:

- Acepta `None` como payload → instancia vacía con defaults.
- Dropea keys que no están en el dataclass (payloads extra no rompen).
- Sustituye valores faltantes / `None` por defaults seguros según tipo: `""` para `str`, `0`/`0.0` para numéricos, `False` para `bool`, `[]` para `list[X]`, instancia vacía para nested `SafeModel`.
- `X | None` explícito → mantiene `None` (opt-in a nullable).

Los campos usan **camelCase (wire format)** verbatim. Esto evita una capa de mapping entre JSON y Python. El file `models.py` está exento de la regla `N815` de ruff (`[tool.ruff.lint.per-file-ignores]` en `pyproject.toml`).

## Alternativas consideradas

### A. `dict[str, Any]` crudo

- **Pro**: cero código de modelo; parsing = `resp.json()`.
- **Contra**: sin autocompletado, sin type checking, sin garantía de acceso seguro. Cada caller tiene que defender contra `KeyError` a mano. Los tests no te salvan porque los fixtures se escriben "completos" y esconden el problema.

### B. Pydantic v2 (`BaseModel` + `model_validate`)

- **Pro**: ecosystem maduro, validación declarativa, `Field(default_factory=...)` cubre los defaults.
- **Contra principal**: Pydantic **valida estrictamente** por defecto. Un payload con un campo faltante (el caso base de Higyrus) falla con `ValidationError` a menos que el campo esté marcado `Optional` con default. Eso significa anotar cada campo con `| None = None` en decenas de modelos — perdemos toda la tipificación fuerte que era la ventaja de Pydantic. Alternativa: usar `model_config = ConfigDict(extra='ignore')` + defaults explícitos, pero terminás escribiendo más código que con dataclasses.
- **Contra secundario**: dependencia pesada (6+ MB, C extensions) para un cliente HTTP fino.

### C. `TypedDict`

- **Pro**: cero runtime overhead, solo hints para el type checker.
- **Contra**: sigue siendo un dict en runtime — `pos["disponibleAjustado"]` rompe con `KeyError` si la key falta. `total=False` ayuda con el type checker pero no cambia el comportamiento runtime. No hay `from_api` ni normalización de defaults.

### D. Dataclasses estándar sin `SafeModel`

- **Pro**: stdlib puro, cero dependencias.
- **Contra**: hay que escribir `default_factory` en cada campo de cada modelo, más un constructor tipo `from_api` por modelo. Mucho boilerplate repetido; alguien se va a olvidar un default y todo revienta. `SafeModel` centraliza la lógica en un solo lugar.

## Consecuencias

### Positivas

- Acceso chaineado (`pos.parking[0].diasParking`) siempre resuelve. El peor caso es `None` o zero-value, nunca una excepción. Esto elimina una clase entera de bugs.
- Los modelos son declarativos — agregar un endpoint nuevo es `@dataclass(frozen=True, slots=True); from_api()` gratis.
- `frozen=True` garantiza que los modelos son hashables y seguros para compartir entre threads.
- `slots=True` reduce memoria cuando hay listas grandes de posiciones/movimientos.

### Negativas / trade-offs aceptados

- **Defaults silenciosos ocultan bugs**: si el API cambia el nombre de una key, no nos enteramos — el campo simplemente queda en su default. Mitigación: tests de integración contra sandbox cuando los tengamos.
- **camelCase en Python**: violamos PEP 8 en `models.py`. Mitigación: el file está explícitamente exento de `N815` con un comentario en `pyproject.toml`. El resto del proyecto sigue snake_case normalmente.
- **No hay validación de tipos runtime**: si el API devuelve un string donde esperábamos un int, `_coerce` lo transforma a `0` silenciosamente. Lo aceptamos porque el API es la fuente de verdad; si un tipo cambia, es un problema upstream.
- **`get_type_hints` cuesta reflection en cada `from_api`**: medido ~5μs por campo. Para responses con 20 campos × 1000 rows hablamos de ~100ms. Aceptable para un cliente HTTP; si se vuelve un problema se cachea con `functools.cache`.

## Referencias

- Ticket Linear: [BEC-80](https://linear.app/gravity-code/issue/BEC-80/foundation-modelos-safe-access-frozen-dataclasses-para-respuestas-del)
- PR: _pendiente_
- Documentación del endpoint piloto: `documentation/higyrus-docs.pdf` pp. 33-36 (`/api/cuentas/{idCuenta}/posiciones`)
- Patrón de referencia inspirador: `matriz-client` ADR-002 — mismo problema (respuestas parciales de Primary API), misma decisión. Nosotros lo adoptamos sin copiar código.
