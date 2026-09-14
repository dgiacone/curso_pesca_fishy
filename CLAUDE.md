# CLAUDE.md — curso pesca fishy MCP Server

Servidor MCP de solo lectura sobre una base de datos Supabase de una empresa pesquera. Expone 13 tools para consultar capturas, lances, embarcaciones y una base de conocimiento RAG.

## Stack

- Python 3.12, FastMCP (`mcp[cli] >= 1.0.0`)
- Supabase (postgrest Python client)
- Gemini API (`gemini-embedding-001`) para embeddings RAG
- Transport: Streamable HTTP (no SSE)
- Deploy: Railway — `https://cursopescafishy-production.up.railway.app/mcp`
- GitHub: `https://github.com/dgiacone/curso_pesca_fishy`

El cliente HTTP está forzado a HTTP/1.1 (workaround para StreamReset en Railway).

## Archivo principal

`server.py` — contiene todas las tools y la configuración del servidor.

## Variables de entorno requeridas

```
SUPABASE_URL
SUPABASE_KEY
GEMINI_API_KEY
```

## Correr localmente

```bash
.venv/bin/python server.py
```

## Tools implementadas (13)

| Tool | Descripción |
|------|-------------|
| `query_table` | SELECT genérico sobre cualquier tabla o vista |
| `list_tables` | Lista tablas disponibles |
| `get_schema(table_name)` | Esquema de una tabla |
| `list_embarcaciones(solo_activas=True)` | Lista embarcaciones |
| `list_documentos` | Lista documentos de la base vectorial |
| `buscar_conocimiento(query, match_count=5)` | Búsqueda semántica RAG via Gemini + RPC `match_documents` |
| `get_capturas_recientes(dias=7)` | Lances de los últimos N días |
| `get_resumen_captura_por_especie(especie?)` | Resumen por especie |
| `get_resumen_captura_por_embarcacion()` | Resumen por barco |
| `get_lances_sin_descarga(matricula?)` | Lances sin descarga registrada |
| `get_excepciones_reconciliacion(matricula?)` | Descargas con diferencias |
| `get_reconciliacion_capturas(matricula?, fecha_desde?, fecha_hasta?, estado?)` | Declarado vs pesado |
| `get_lances_detalle(matricula?, fecha_desde?, fecha_hasta?, especie?)` | Detalle de lances |

Las tools de captura consultan vistas: `vista_lances_detalle`, `vista_reconciliacion_capturas`, etc.

## Convenciones críticas

- **Solo lectura** — nunca generar INSERT, UPDATE ni DELETE.
- Parámetros opcionales ausentes: usar `None`, nunca string vacío.
- Sin resultados: devolver `"No se encontraron resultados para esos filtros."`
- Error de DB: devolver `"No se pudo consultar la base de datos: <detalle>"`

## Setup de base de datos

`setup.sql` crea las RPCs `get_tables_info` y `get_table_schema` en Supabase. Debe ejecutarse una sola vez. La búsqueda RAG usa la tabla `documentos` + RPC `match_documents`.
