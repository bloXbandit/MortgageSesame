"""
In-memory rate limiting middleware.

Production note: swap this for Redis-backed slowapi or starlette-rate-limit
when deploying to Railway/Render. This is a safety net, not a load balancer.
"""

import time
from collections import defaultdict
from fastapi import Request, HTTPException
from starlette.middleware.base import BaseHTTPMiddleware

_window = 60  # seconds
_limits = {
    "/api/v1/auth/login": (5, 60),      # 5 per minute — login brute force
    "/api/v1/auth/refresh": (10, 60),   # 10 per minute — token refresh
    "/api/v1/agent/": (30, 60),        # 30 per minute — agent API
    "global": (120, 60),                # 120 req/min per IP blanket
}

# {ip: [(timestamp, path), ...]}
_buckets: dict[str, list[tuple[float, str]]] = defaultdict(list)


def _clean(ip: str, now: float):
    cutoff = now - _window
    _buckets[ip] = [(t, p) for (t, p) in _buckets[ip] if t > cutoff]


def _count(ip: str, path: str, now: float, window: float) -> int:
    cutoff = now - window
    return sum(1 for t, p in _buckets[ip] if t > cutoff and (path.startswith(p) or p == "global"))


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Only rate-limit API routes
        path = request.url.path
        if not path.startswith("/api/"):
            return await call_next(request)

        ip = request.client.host if request.client else "unknown"
        now = time.time()
        _clean(ip, now)

        # Check specific route limits first, then global
        for prefix, (limit, window) in _limits.items():
            if path.startswith(prefix) or prefix == "global":
                if _count(ip, path, now, window) >= limit:
                    raise HTTPException(
                        status_code=429,
                        detail="Rate limit exceeded. Slow down or retry later."
                    )

        # Record the hit
        _buckets[ip].append((now, path))
        response = await call_next(request)
        return response
