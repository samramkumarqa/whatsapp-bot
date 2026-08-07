"""
Global admin-session gate - see main.py for wiring and api/auth.py for
the login/logout routes this depends on.

There's no per-business login yet (see the ongoing multi-tenancy work in
crm/customer_mapping.py, automation/*, api/businesses.py), so for now
every page and API route requires the single shared admin account,
except a small allowlist of endpoints that can't go through a login
flow at all - Twilio's webhook (called by Twilio's servers, not a
browser) and the health check.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse

EXEMPT_PATHS = {
    "/login",
    "/logout",
    "/webhook",
    "/health",
}


class AdminAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        if request.url.path in EXEMPT_PATHS:
            return await call_next(request)

        if request.session.get("role") == "admin":
            return await call_next(request)

        # Not authenticated. A real browser navigating to a page sends
        # "text/html" in Accept; the dashboard/settings/businesses pages'
        # own fetch() calls don't set an Accept header at all (defaults
        # to "*/*" in every browser), so this reliably tells a full page
        # load apart from an XHR/fetch call without needing every one of
        # those ~30 fetch() call sites to be touched - a stale page a
        # user already had open just gets JSON 401s from its fetch()
        # calls instead of silently redirecting mid-interaction.
        accept = request.headers.get("accept", "")

        if "text/html" in accept:

            return RedirectResponse(
                url="/login",
                status_code=302
            )

        return JSONResponse(
            {
                "status": "error",
                "detail": "Not authenticated"
            },
            status_code=401
        )
