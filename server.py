import os
import httpx
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

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


mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.streamable_http_app()

if __name__ == "__main__":
    mcp.run(transport="streamable-http")
