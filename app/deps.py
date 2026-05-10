"""FastAPI dependencies backed by app.state (lifespan-managed resources)."""

from fastapi import Request
import httpx


def get_http_client(request: Request) -> httpx.AsyncClient:
    """Shared AsyncClient for outbound HTTP (OpenAI, webhooks, etc.)."""
    return request.app.state.http_client


def get_redis(request: Request):
    """Optional Redis client; None when REDIS_URL is unset."""
    return getattr(request.app.state, "redis", None)
