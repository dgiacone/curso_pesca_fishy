import os
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP
from supabase import create_client, Client

load_dotenv()

SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_KEY"]
MCP_AUTH_TOKEN = os.environ["MCP_AUTH_TOKEN"]

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

mcp = FastMCP("ara virtual coo")


class BearerAuthMiddleware:
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] == "http":
            headers = dict(scope.get("headers", []))
            auth = headers.get(b"authorization", b"").decode()
            if auth != f"Bearer {MCP_AUTH_TOKEN}":
                body = b'{"error": "Unauthorized"}'
                await send({"type": "http.response.start", "status": 401, "headers": [(b"content-type", b"application/json"), (b"content-length", str(len(body)).encode())]})
                await send({"type": "http.response.body", "body": body})
                return
        await self.app(scope, receive, send)


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


app = BearerAuthMiddleware(mcp.sse_app(host="0.0.0.0"))

if __name__ == "__main__":
    mcp.run()
