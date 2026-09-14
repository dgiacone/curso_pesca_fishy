import os
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
GEMINI_API_KEY = os.environ["GEMINI_API_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Replace the postgrest httpx session with one that forces HTTP/1.1
# to avoid StreamReset errors (h2 PROTOCOL_ERROR) in some cloud environments
try:
    _old = supabase.postgrest.session
    supabase.postgrest.session = httpx.Client(
        base_url=str(_old.base_url),
        headers=dict(_old.headers),
        http2=False,
        timeout=30.0,
    )
except Exception:
    pass

mcp = FastMCP("curso pesca fishy")


@mcp.tool()
def list_embarcaciones(solo_activas: bool = True) -> list[dict]:
    """Lista las embarcaciones registradas.

    Args:
        solo_activas: Si es True (por defecto), devuelve solo las embarcaciones activas.
    """
    query = supabase.table("embarcaciones").select(
        "matricula, nombre, patron_habitual, eslora_m, capacidad_bodega_kg, tipo_flota, activa"
    ).order("nombre")
    if solo_activas:
        query = query.eq("activa", True)
    return query.execute().data


@mcp.tool()
def list_tables() -> list[dict]:
    """Lista todas las tablas disponibles en la base de datos de Supabase."""
    result = supabase.rpc("get_tables_info", {}).execute()
    return result.data


@mcp.tool()
def get_schema(table_name: str) -> list[dict]:
    """Devuelve las columnas y tipos de datos de una tabla específica.

    Args:
        table_name: Nombre de la tabla a inspeccionar.
    """
    result = supabase.rpc("get_table_schema", {"p_table_name": table_name}).execute()
    return result.data


GEMINI_EMBED_URL = (
    "https://generativelanguage.googleapis.com/v1/models/"
    "gemini-embedding-001:embedContent?key={key}"
)

_NO_RESULTS = "No se encontraron resultados para esos filtros."


def _db_error(e: Exception) -> str:
    return f"No se pudo consultar la base de datos: {e}"


@mcp.tool()
def get_lances_detalle(
    matricula: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    especie: str | None = None,
) -> list[dict] | str:
    """Devuelve el detalle de los lances de pesca registrados, con los datos
    de la embarcación ya resueltos (matrícula, nombre, patrón). Usar
    cuando se pregunte por lances de una embarcación específica, de una
    especie puntual, o de un rango de fechas. No incluye información de
    descarga — para eso usar get_reconciliacion_capturas.

    Args:
        matricula: Matrícula de la embarcación, ej. 'PM-0231'.
        fecha_desde: Fecha mínima del lance (YYYY-MM-DD, inclusive).
        fecha_hasta: Fecha máxima del lance (YYYY-MM-DD, inclusive).
        especie: Filtra por especie exacta, ej. 'Merluza'.
    """
    try:
        q = supabase.table("vista_lances_detalle").select("*")
        if matricula:
            q = q.eq("matricula", matricula)
        if fecha_desde:
            q = q.gte("fecha", fecha_desde)
        if fecha_hasta:
            q = q.lte("fecha", fecha_hasta)
        if especie:
            q = q.eq("especie", especie)
        data = q.order("fecha", desc=True).order("hora", desc=True).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_reconciliacion_capturas(
    matricula: str | None = None,
    fecha_desde: str | None = None,
    fecha_hasta: str | None = None,
    estado: str | None = None,
) -> list[dict] | str:
    """Compara, para cada lance ya descargado, lo declarado a bordo contra
    lo efectivamente pesado en puerto — incluye la diferencia en kg, en
    porcentaje, y el estado ('confirmado' o 'excepcion'). Usar cuando se
    pregunte si hubo discrepancias entre captura y descarga, o para auditar
    una embarcación o un rango de fechas puntual.

    Args:
        matricula: Matrícula de la embarcación.
        fecha_desde: Fecha mínima del lance (YYYY-MM-DD).
        fecha_hasta: Fecha máxima del lance (YYYY-MM-DD).
        estado: 'confirmado' o 'excepcion'.
    """
    try:
        q = supabase.table("vista_reconciliacion_capturas").select("*")
        if matricula:
            q = q.eq("matricula", matricula)
        if fecha_desde:
            q = q.gte("fecha_lance", fecha_desde)
        if fecha_hasta:
            q = q.lte("fecha_lance", fecha_hasta)
        if estado:
            q = q.eq("estado", estado)
        data = q.order("fecha_lance", desc=True).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_excepciones_reconciliacion(
    matricula: str | None = None,
) -> list[dict] | str:
    """Devuelve únicamente las descargas marcadas como 'excepcion' — casos
    donde la diferencia entre lo declarado y lo pesado superó el umbral
    permitido. Usar para preguntas del tipo '¿hay algo raro en las descargas?'
    o '¿qué barcos tuvieron diferencias importantes?'.

    Args:
        matricula: Restringe a una embarcación puntual.
    """
    try:
        q = supabase.table("vista_excepciones_reconciliacion").select("*")
        if matricula:
            q = q.eq("matricula", matricula)
        data = q.order("fecha_lance", desc=True).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_lances_sin_descarga(
    matricula: str | None = None,
) -> list[dict] | str:
    """Devuelve los lances que todavía no tienen una descarga registrada —
    capturas pendientes de cierre operativo. Usar para preguntas del tipo
    '¿qué falta descargar?' o para detectar demoras en el registro.

    Args:
        matricula: Restringe a una embarcación puntual.
    """
    try:
        q = supabase.table("vista_lances_sin_descarga").select("*")
        if matricula:
            q = q.eq("matricula", matricula)
        data = q.order("fecha", desc=True).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_resumen_captura_por_embarcacion() -> list[dict] | str:
    """Devuelve un resumen agregado por embarcación: cantidad de lances,
    kg total declarado, kg total pesado, diferencia promedio y cantidad
    de excepciones. Siempre incluye todas las embarcaciones registradas,
    incluso las sin actividad. Usar para '¿cómo viene la flota?' o para
    comparar embarcaciones entre sí.
    """
    try:
        data = (
            supabase.table("vista_resumen_captura_por_embarcacion")
            .select("*")
            .order("matricula")
            .execute()
            .data
        )
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_resumen_captura_por_especie(
    especie: str | None = None,
) -> list[dict] | str:
    """Devuelve el total de kg declarados, cantidad de lances y promedio
    por lance, agrupado por especie. Usar para '¿cuánto se capturó de tal
    especie?' o para comparar especies entre sí.

    Args:
        especie: Restringe el resumen a una especie puntual.
    """
    try:
        q = supabase.table("vista_resumen_captura_por_especie").select("*")
        if especie:
            q = q.eq("especie", especie)
        data = q.order("kg_total_declarado", desc=True).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def get_capturas_recientes(dias: int = 7) -> list[dict] | str:
    """Devuelve los lances de los últimos N días (por defecto 7), con los
    datos de embarcación resueltos. El rango se calcula en el momento de
    la consulta. Usar para '¿qué pasó esta semana?' o '¿hubo actividad reciente?'.

    Args:
        dias: Cantidad de días hacia atrás desde hoy (default 7).
    """
    try:
        from datetime import date, timedelta
        fecha_desde = (date.today() - timedelta(days=dias)).isoformat()
        data = (
            supabase.table("vista_lances_detalle")
            .select("*")
            .gte("fecha", fecha_desde)
            .order("fecha", desc=True)
            .order("hora", desc=True)
            .execute()
            .data
        )
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


@mcp.tool()
def buscar_conocimiento(query: str, match_count: int = 5) -> list[dict] | str:
    """Busca en la base de conocimiento documentos relevantes usando similitud semántica.
    Embedea la consulta con Gemini text-embedding-004 y llama al RPC match_documentos
    en Supabase. Usar para preguntas sobre reglamentos, procedimientos o cualquier
    contenido cargado como documento.

    Args:
        query: Pregunta o texto a buscar.
        match_count: Cantidad máxima de resultados (default 5).
    """
    try:
        embed_resp = httpx.post(
            GEMINI_EMBED_URL.format(key=GEMINI_API_KEY),
            json={
                "model": "models/gemini-embedding-001",
                "content": {"parts": [{"text": query}]},
            },
            timeout=15.0,
        )
        embed_resp.raise_for_status()
        embedding = embed_resp.json()["embedding"]["values"]

        data = supabase.rpc(
            "match_documents",
            {"query_embedding": embedding, "match_count": match_count},
        ).execute().data
        return data or _NO_RESULTS
    except Exception as e:
        return _db_error(e)


mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
