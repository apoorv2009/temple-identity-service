from fastapi import FastAPI

from app.api.router import api_router

app = FastAPI(
    title="Temple Identity Service",
    version="0.1.0",
    summary="Password-based identity service for approved devotees and admins.",
)
app.include_router(api_router)

