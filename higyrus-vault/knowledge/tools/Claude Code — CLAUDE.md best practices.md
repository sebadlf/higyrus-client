---
tags: [tools, claude-code]
---

# CLAUDE.md — Best Practices

## Qué incluir siempre

1. **Project Overview** — 2-3 oraciones. Qué, para quién, por qué.
2. **Development Commands** — copy-paste-able. `uv sync`, `npm install`, etc.
3. **Architecture** — módulos principales, flujo de datos, patrones no-obvios.
4. **Conventions** — naming, error handling, lo que no se deduce del código.
5. **External References** — links a Linear, docs, vault de Obsidian.

## Qué NO incluir

- Documentación exhaustiva de la API (mejor linkear al archivo de spec)
- Historial de cambios (eso es git)
- TODOs (eso es Linear)
- Instrucciones genéricas de Python/Node (Claude ya sabe)

## Tips

- **Documentar lo contraintuitivo**: si algo parece un bug pero no lo es, explicarlo en CLAUDE.md evita que Claude lo "arregle"
- **Actualizar con el proyecto**: CLAUDE.md desactualizado es peor que no tenerlo
- **Ser específico con comandos**: `uv run python main.py` es mejor que "correr el script"
- **Incluir restricciones**: "no usar async porque X", "no tocar este módulo porque Y"

## Jerarquía de CLAUDE.md

Claude Code lee CLAUDE.md en orden de prioridad:
1. `CLAUDE.md` en el directorio actual (proyecto)
2. `~/.claude/CLAUDE.md` (global, para todos los proyectos)

Usar el global para preferencias generales (estilo, idioma) y el de proyecto para contexto específico.
