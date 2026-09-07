import os
import socket
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

mcp = FastMCP("ara virtual coo")


@mcp.tool()
def diagnostico() -> dict:
    """Verifica la configuración y conectividad del servidor."""
    hostname = SUPABASE_URL.replace("https://", "").split("/")[0]
    dns_ok = False
    dns_error = ""
    try:
        socket.getaddrinfo(hostname, 443)
        dns_ok = True
    except Exception as e:
        dns_error = str(e)
    return {
        "supabase_url": SUPABASE_URL,
        "supabase_key_set": bool(SUPABASE_KEY),
        "dns_resolved": dns_ok,
        "dns_error": dns_error,
    }


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


@mcp.tool()
def query_table(
    table_name: str,
    columns: str = "*",
    filters: dict | None = None,
    limit: int = 100,
    offset: int = 0,
) -> list[dict]:
    """Ejecuta un SELECT en una tabla de Supabase y devuelve los resultados.

    Args:
        table_name: Nombre de la tabla a consultar.
        columns: Columnas a seleccionar, separadas por coma (por defecto todas).
        filters: Diccionario de filtros {columna: valor} aplicados como igualdad exacta.
        limit: Cantidad máxima de filas a retornar (máximo 1000).
        offset: Cantidad de filas a saltar (paginación).
    """
    limit = min(limit, 1000)
    query = supabase.table(table_name).select(columns).range(offset, offset + limit - 1)

    if filters:
        for column, value in filters.items():
            query = query.eq(column, value)

    result = query.execute()
    return result.data


mcp.settings.transport_security = TransportSecuritySettings(enable_dns_rebinding_protection=False)
app = mcp.sse_app()

if __name__ == "__main__":
    mcp.run()
