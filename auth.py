"""
Session/auth helpers shared across the app:

- verify_admin_login() - the single shared admin account (see
  main.py's AdminAuthMiddleware and api/auth.py's /login routes).
  There's no user table for this - just one username/bcrypt-hash pair
  in config.py (ADMIN_USERNAME/ADMIN_PASSWORD_HASH env vars).

- enforce_tenant_access() - the actual security boundary for real
  per-business login (see api/auth.py's /business-login routes). Every
  API route that takes a `user_id` path param calls this first; it's
  what stops a logged-in business owner from viewing another business's
  data by editing a URL or replaying a request with a different
  user_id, regardless of what the frontend's hidden input happens to
  send.

- resolve_dashboard_user_id() - picks which business's dashboard/
  analytics/settings pages should render for the current session:
  always the business owner's own business for a business_owner
  session, or an admin-selectable business (via ?business=, remembered
  in session) for an admin session.
"""

import secrets

import bcrypt
from fastapi import HTTPException, Request

from config import ADMIN_USERNAME, ADMIN_PASSWORD_HASH


def verify_admin_login(username: str, password: str) -> bool:
    """
    True only if both the username and password match the configured
    admin account. Both checks always run (rather than short-circuiting
    on a bad username) so a failed login doesn't leak, via response
    timing, whether the username or the password was the wrong part.
    """

    if not ADMIN_USERNAME or not ADMIN_PASSWORD_HASH:
        # Misconfigured deployment (env vars not set) - fail closed
        # rather than letting every login through.
        return False

    username_ok = secrets.compare_digest(
        username.encode("utf-8"),
        ADMIN_USERNAME.encode("utf-8")
    )

    try:
        password_ok = bcrypt.checkpw(
            password.encode("utf-8"),
            ADMIN_PASSWORD_HASH.encode("utf-8")
        )
    except ValueError:
        # Malformed hash in config - fail closed instead of raising.
        password_ok = False

    return username_ok and password_ok


def enforce_tenant_access(request: Request, user_id: str) -> None:
    """
    Raises 403 unless the current session is allowed to see `user_id`'s
    data. Admin sessions bypass this entirely (admin sees every
    business, per the original scope of the login work). A
    business_owner session may only access its own business's user_id -
    this is checked against request.session, not anything the client
    sent, so it can't be bypassed by editing the hidden #userId input or
    hand-crafting an API call with a different user_id in the URL.

    Call this as the first line of every route that takes `user_id` as
    a path param.
    """

    role = request.session.get("role")

    if role == "admin":
        return

    if role == "business_owner" and request.session.get("user_id") == user_id:
        return

    raise HTTPException(
        status_code=403,
        detail="Not authorized for this business",
    )


async def enforce_tenant_access_for_customer(request: Request, customer_phone: str) -> None:
    """
    Same rule as enforce_tenant_access(), for the many customer-detail
    routes (crm/lead/activity/timeline/opportunities in api/customer.py)
    that are keyed by customer_phone instead of user_id. Resolves which
    business that customer_phone belongs to first (a single query - see
    crm.customer_mapping.get_owning_business_user_id()), then applies
    the same admin-bypass / business_owner-must-match rule. A
    customer_phone that doesn't resolve to any business - unknown
    number, or a business a business_owner session doesn't own - is
    treated as not authorized, same as a mismatched user_id.

    `async` (unlike enforce_tenant_access(), which is pure session
    lookups with no I/O) because this one runs a real sqlite query -
    routing it through run_in_threadpool keeps that off the event loop,
    consistent with every other blocking DB call in this codebase (see
    e.g. api/dashboard.py's module docstring). Admin sessions short
    -circuit before that query even runs.
    """

    if request.session.get("role") == "admin":
        return

    from fastapi.concurrency import run_in_threadpool
    from crm.customer_mapping import get_owning_business_user_id

    owning_user_id = await run_in_threadpool(
        get_owning_business_user_id, customer_phone
    )

    enforce_tenant_access(request, owning_user_id)


async def resolve_dashboard_user_id(request: Request):
    """
    Which business's user_id the dashboard/analytics/settings pages
    should render for the current session (see api/misc.py's page
    routes, which pass this into the template as `user_id`).

    - business_owner: always their own business, from the session set
      at login - never client-influenced. No DB lookup needed.
    - admin: no business of their own, so admin can browse any business
      via ?business=<user_id> (see templates/businesses.html's "View
      Dashboard" links). The chosen business is remembered in the
      session so navigating between pages doesn't lose it; falls back
      to the first active business if nothing's been picked yet - that
      fallback is the only branch here that touches the database
      (get_active_businesses()), which is why this function is async
      and routes through run_in_threadpool, consistent with every other
      blocking DB call in this codebase.
    - anything else (shouldn't happen - AdminAuthMiddleware would have
      already redirected to a login page): None.
    """

    role = request.session.get("role")

    if role == "business_owner":
        return request.session.get("user_id")

    if role == "admin":

        business_param = request.query_params.get("business")

        if business_param:
            request.session["viewing_user_id"] = business_param
            return business_param

        viewing = request.session.get("viewing_user_id")

        if viewing:
            return viewing

        from fastapi.concurrency import run_in_threadpool
        from crm.customer_mapping import get_active_businesses

        active = await run_in_threadpool(get_active_businesses)

        return active[0]["user_id"] if active else None

    return None
