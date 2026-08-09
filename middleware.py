"""
Global session gate - see main.py for wiring and api/auth.py for the
login/logout routes this depends on.

Two roles exist:
  - "admin"          - the single shared admin account. Sees every page,
                        including the Businesses registry.
  - "business_owner" - a real per-business login via WhatsApp/SMS OTP
                        (Twilio Verify - see verify.py). Scoped to their
                        own business everywhere except the Businesses
                        registry, which is admin-only.

Everything except a small allowlist of endpoints that can't go through
either login flow at all requires one of the two roles - Twilio's
webhook (called by Twilio's servers, not a browser) and the health
check.
"""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse, JSONResponse

EXEMPT_PATHS = {
    "/login",
    "/logout",
    "/business-login",
    "/business-login/verify",
    "/webhook",
    "/health",
}

# Admin-only page/API prefixes - a business_owner session is redirected
# away from these rather than getting a 403 page, since this is normal
# navigation (e.g. a stale bookmark) rather than someone probing for
# access.
ADMIN_ONLY_PREFIXES = (
    "/businesses",
    "/business-registry",
)


class AdminAuthMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request, call_next):

        path = request.url.path

        if path in EXEMPT_PATHS:
            return await call_next(request)

        role = request.session.get("role")

        if role == "admin":
            return _no_store(await call_next(request))

        if role == "business_owner":

            if path.startswith(ADMIN_ONLY_PREFIXES):

                accept = request.headers.get("accept", "")

                if "text/html" in accept:
                    return RedirectResponse(url="/", status_code=302)

                return JSONResponse(
                    {
                        "status": "error",
                        "detail": "Not authorized for this page"
                    },
                    status_code=403
                )

            return _no_store(await call_next(request))

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


def _no_store(response):
    """
    Every authenticated page ("/", /settings, /follow-ups, /analytics,
    /businesses...) is rendered per-session, with a business's own id
    baked directly into the HTML (see e.g. dashboard.html's hidden
    #userId input). Without an explicit no-store, the browser is free to
    keep a cached copy of that HTML and replay it after the session
    changes - e.g. an admin switches which business they're viewing, or
    someone logs out and a different business owner logs in on the same
    browser - showing (and, worse, having page JS fetch data scoped to)
    a business the *current* session no longer has access to. This
    reproduced live as an "automation/rules/<old business>" call
    returning 403 against a freshly-authenticated session, because the
    HTML shell itself was served stale with the previous session's
    business id already baked in. Applied here rather than per-route so
    every session-scoped page is covered by construction, not by
    remembering to add a header to each new route.
    """

    response.headers["Cache-Control"] = "no-store"

    return response
