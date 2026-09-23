import os
import asyncpg
import sqlparse
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Optional
from contextlib import asynccontextmanager

# Replace 'YOUR_POSTGRES_PASSWORD' with your actual pgAdmin/PostgreSQL password
DATABASE_URL = os.getenv(
    "DATABASE_URL", 
    "postgresql://postgres:vinayAPI@localhost:5432/incident_db"
)

pool: Optional[asyncpg.Pool] = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global pool
    # Initialize asyncpg connection pool on startup
    pool = await asyncpg.create_pool(DATABASE_URL, min_size=2, max_size=10)
    yield
    # Close pool cleanly on shutdown
    if pool:
        await pool.close()

app = FastAPI(title="Diagnostic DB Backend Engine", lifespan=lifespan)

@app.get("/")
async def root():
    return {
        "status": "healthy",
        "service": "Database Incident Assistant Backend",
        "docs_url": "http://127.0.0.1:8000/docs"
    }

class QueryRequest(BaseModel):
    query: str

class LogFilterRequest(BaseModel):
    service_name: Optional[str] = None
    min_latency: Optional[int] = None
    level: Optional[str] = None

def validate_sql_safety(query: str):
    parsed = sqlparse.parse(query)
    if not parsed:
        raise HTTPException(status_code=400, detail="Invalid SQL statement.")
    
    # AST Token Inspection: Enforce strictly read-only SELECT statements
    for statement in parsed:
        first_token = statement.get_type()
        if first_token != "SELECT":
            raise HTTPException(
                status_code=403, 
                detail=f"Destructive or mutating operation blocked: '{first_token}' is not allowed."
            )

@app.post("/execute-safe-query")
async def execute_safe_query(payload: QueryRequest):
    validate_sql_safety(payload.query)
    async with pool.acquire() as conn:
        try:
            records = await conn.fetch(payload.query)
            return [dict(record) for record in records]
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@app.get("/schema")
async def get_schema_metadata():
    query = """
    SELECT table_name, column_name, data_type 
    FROM information_schema.columns 
    WHERE table_schema = 'public'
    ORDER BY table_name, ordinal_position;
    """
    async with pool.acquire() as conn:
        records = await conn.fetch(query)
        return [dict(r) for r in records]

@app.post("/filter-logs")
async def filter_logs(payload: LogFilterRequest):
    query = "SELECT * FROM service_logs WHERE 1=1"
    args = []
    
    if payload.service_name:
        args.append(payload.service_name)
        query += f" AND service_name = ${len(args)}"
    if payload.min_latency:
        args.append(payload.min_latency)
        query += f" AND latency_ms >= ${len(args)}"
    if payload.level:
        args.append(payload.level)
        query += f" AND level = ${len(args)}"
        
    query += " ORDER BY created_at DESC LIMIT 50;"
    
    async with pool.acquire() as conn:
        records = await conn.fetch(query, *args)
        return [dict(r) for r in records]