---
tags: [workflow]
---

# Workflow de desarrollo integrado

Claude Code + Obsidian + Linear + GitHub

## Flujo diario

### 1. Arrancar el día (5 min)

- Revisar el ciclo actual en **Linear** — qué issues están en progreso, cuáles son prioridad
- Crear el **daily log** en Obsidian (usar template `tpl-daily-log`)
- Elegir el issue a trabajar

### 2. Antes de codear (5-10 min)

- Leer la nota de dominio relevante en **Obsidian** si el issue toca algo que no tenés fresco
- Si es una decisión importante → crear un draft de **ADR** en Obsidian antes de implementar
- Mover el issue a "In Progress" en **Linear**

### 3. Implementar (el grueso del día)

- Abrir **Claude Code** en el repo
- Darle contexto: "Estoy trabajando en [Linear issue]. El objetivo es [X]. Contexto relevante: [Y]"
- Claude Code implementa, vos revisás
- Usar `/commit` para commits descriptivos
- Crear PR con link al issue de Linear

### 4. Review y merge (15 min)

- Claude Code puede hacer `/review` del PR
- Si hay feedback → iterar
- Merge → Linear auto-cierra el issue

### 5. Capturar conocimiento (5 min)

- ¿Aprendiste algo nuevo de dominio? → nota en **Obsidian** `domain/`
- ¿Tomaste una decisión arquitectónica? → **ADR** en Obsidian
- ¿Claude Code hizo algo que querés que repita/evite? → feedback en **Claude Code memory**
- Actualizar el **daily log**

## Flujo para nueva feature (multi-día)

```
Linear issue (define qué)
    → Obsidian ADR (decide cómo)
        → GitHub branch (implementa)
            → Claude Code (ejecuta)
                → GitHub PR (revisa)
                    → Linear auto-close (cierra el loop)
                        → Obsidian (captura aprendizajes)
```

## Flujo para bug fix (mismo día)

```
Bug reportado (Linear o GitHub issue)
    → Claude Code investiga (lee código, reproduce)
        → Fix + test
            → PR con link al issue
                → Merge → auto-close
```

## Flujo para exploración / spike

```
Pregunta abierta
    → Obsidian nota "Exploración: [tema]"
        → Claude Code investiga (puede leer APIs, código, docs)
            → Resultado → actualizar nota en Obsidian
                → Si hay trabajo a hacer → crear Linear issue
```

## Principios

1. **Linear es el backlog, no Obsidian** — las notas no reemplazan issues
2. **Obsidian es el cerebro, no Linear** — el contexto rico vive en notas, no en descriptions de issues
3. **GitHub es la verdad, no Obsidian** — el código actual siempre gana sobre notas desactualizadas
4. **Claude Code es el ejecutor, no el planificador** — planificá en Linear/Obsidian, ejecutá con Claude Code
5. **Capturá mientras está fresco** — 5 minutos de notas hoy ahorra 30 minutos de re-descubrimiento mañana
