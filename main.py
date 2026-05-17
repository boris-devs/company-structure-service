from fastapi import FastAPI
from src.routers import departments_router

app = FastAPI()

prefix = "/api/v1"

app.include_router(router=departments_router, prefix=f"{prefix}/departments", tags=["departments"])
