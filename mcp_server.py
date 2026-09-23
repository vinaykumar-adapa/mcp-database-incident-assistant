import httpx
from mcp.server import MCPServer

# Initialize the MCPServer (v2 SDK standard)
mcp = MCPServer("Database-Incident-Assistant")
FASTAPI_BASE_URL = "http://127.0.0.1:8000"

# 1. MCP Resource: Expose DB schema
@mcp.resource("postgres://schema")
async def get_db_schema() -> str:
    """Provides the public tables and column structures of the target database."""
    async with httpx.AsyncClient() as client:
        res = await client.get(f"{FASTAPI_BASE_URL}/schema")
        return res.text

# 2. MCP Tool: Diagnostic safe queries
@mcp.tool()
async def execute_diagnostic_query(query: str) -> str:
    """Executes a strictly read-only SELECT query against the incident database."""
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{FASTAPI_BASE_URL}/execute-safe-query", 
            json={"query": query},
            timeout=10.0
        )
        return res.text

# 3. MCP Tool: Incident log search
@mcp.tool()
async def search_incident_logs(
    service_name: str = "", 
    min_latency_ms: int = 0, 
    log_level: str = ""
) -> str:
    """Filters incident logs by service name, latency threshold, or level (ERROR, WARN)."""
    payload = {
        "service_name": service_name if service_name else None,
        "min_latency": min_latency_ms if min_latency_ms > 0 else None,
        "level": log_level if log_level else None
    }
    async with httpx.AsyncClient() as client:
        res = await client.post(
            f"{FASTAPI_BASE_URL}/filter-logs", 
            json=payload,
            timeout=10.0
        )
        return res.text

if __name__ == "__main__":
    mcp.run()