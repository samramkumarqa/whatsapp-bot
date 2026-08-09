"""
Tests for the login gates - auth.py's credential/session-access checks,
and the end-to-end behavior of api/auth.py's login/logout routes plus
middleware.py's AdminAuthMiddleware (session-gates every route except
/login, /logout, /business-login(/verify), /webhook, /health - see
main.py for wiring).

Two roles exist:
  - admin: the single shared admin account (unchanged from before).
  - business_owner: real per-business login via WhatsApp/SMS OTP
    (Twilio Verify - see verify.py). verify.send_otp()/check_otp() are
    monkeypatched throughout so these tests never hit the real Twilio
    API.

The middleware tests build a small standalone FastAPI app (SessionMiddleware
+ AdminAuthMiddleware + api/auth.py + a couple of dummy protected routes)
rather than importing the real main.py, since main.py pulls in
api/webhook.py's RAG chain (langchain_huggingface etc.), which has nothing
to do with auth and isn't otherwise needed here.
"""

import asyncio

import bcrypt
import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

import auth
from auth import (
    enforce_tenant_access,
    enforce_tenant_access_for_customer,
    resolve_dashboard_user_id,
    verify_admin_login,
)
from api.auth import router as auth_router
from crm.customer_mapping import register_business, save_mapping, set_business_status
from middleware import AdminAuthMiddleware
from tests.conftest import FakeRequest


# ---------------------------------------------------------------------
# auth.py - verify_admin_login()
# ---------------------------------------------------------------------

@pytest.fixture
def admin_creds(monkeypatch):
    password_hash = bcrypt.hashpw(b"correct-horse", bcrypt.gensalt()).decode()
    monkeypatch.setattr(auth, "ADMIN_USERNAME", "testadmin")
    monkeypatch.setattr(auth, "ADMIN_PASSWORD_HASH", password_hash)


def test_verify_admin_login_accepts_correct_credentials(admin_creds):
    assert verify_admin_login("testadmin", "correct-horse") is True


def test_verify_admin_login_rejects_wrong_password(admin_creds):
    assert verify_admin_login("testadmin", "wrong-password") is False


def test_verify_admin_login_rejects_wrong_username(admin_creds):
    assert verify_admin_login("someone-else", "correct-horse") is False


def test_verify_admin_login_rejects_both_wrong(admin_creds):
    assert verify_admin_login("nobody", "nothing") is False


def test_verify_admin_login_fails_closed_when_unconfigured(monkeypatch):
    monkeypatch.setattr(auth, "ADMIN_USERNAME", None)
    monkeypatch.setattr(auth, "ADMIN_PASSWORD_HASH", None)

    assert verify_admin_login("admin", "admin") is False


def test_verify_admin_login_fails_closed_on_malformed_hash(monkeypatch):
    monkeypatch.setattr(auth, "ADMIN_USERNAME", "testadmin")
    monkeypatch.setattr(auth, "ADMIN_PASSWORD_HASH", "not-a-real-bcrypt-hash")

    assert verify_admin_login("testadmin", "anything") is False


# ---------------------------------------------------------------------
# middleware.py + api/auth.py - end-to-end via a minimal test app
# ---------------------------------------------------------------------

def _build_test_app():

    app = FastAPI()

    app.add_middleware(AdminAuthMiddleware)
    app.add_middleware(
        SessionMiddleware,
        secret_key="test-secret-key",
        session_cookie="wp_session",
    )

    app.include_router(auth_router)

    @app.get("/protected-page")
    async def protected_page():
        return {"status": "success", "secret": "dashboard data"}

    # Stands in for the real /businesses page (admin-only, see
    # middleware.py's ADMIN_ONLY_PREFIXES) without pulling in the real
    # router/templates.
    @app.get("/businesses")
    async def fake_businesses_page():
        return {"status": "success", "businesses": []}

    @app.get("/webhook")
    async def fake_webhook_get():
        # Real /webhook is POST-only, but the exemption is path-based -
        # this only exists to prove the path itself is exempt.
        return {"status": "ok"}

    @app.get("/health")
    async def health():
        return {"status": "alive"}

    return app


@pytest.fixture
def client(admin_creds):
    return TestClient(_build_test_app())


def test_protected_route_without_session_returns_401_json(client):
    response = client.get(
        "/protected-page", headers={"accept": "application/json"}
    )
    assert response.status_code == 401


def test_protected_route_without_session_redirects_html_requests(client):
    response = client.get(
        "/protected-page",
        headers={"accept": "text/html"},
        follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/login"


def test_webhook_and_health_are_exempt_without_login(client):
    assert client.get("/webhook").status_code == 200
    assert client.get("/health").status_code == 200


def test_login_page_loads_without_a_session(client):
    response = client.get("/login")
    assert response.status_code == 200
    assert "Sign In" in response.text


def test_login_with_wrong_credentials_redirects_with_error(client):
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "wrong"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/login?error=1"

    # The still-unauthenticated session must not be able to reach the
    # protected route after a failed attempt.
    protected = client.get(
        "/protected-page", headers={"accept": "application/json"}
    )
    assert protected.status_code == 401


def test_login_with_correct_credentials_grants_access(client):
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "correct-horse"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    # The session cookie set by the login response is reused by the
    # TestClient's persistent session for subsequent requests.
    protected = client.get("/protected-page")
    assert protected.status_code == 200
    assert protected.json()["secret"] == "dashboard data"


def test_login_rate_limited_after_too_many_failed_attempts(client):
    for _ in range(5):
        response = client.post(
            "/login",
            data={"username": "testadmin", "password": "wrong"},
            follow_redirects=False
        )
        assert response.headers["location"] == "/login?error=1"

    # The 6th attempt is rejected on the rate limit, even with the
    # *correct* password - proves the check runs before
    # verify_admin_login(), not just after N failures specifically.
    response = client.post(
        "/login",
        data={"username": "testadmin", "password": "correct-horse"},
        follow_redirects=False
    )
    assert response.headers["location"] == "/login?error=ratelimited"

    protected = client.get(
        "/protected-page", headers={"accept": "application/json"}
    )
    assert protected.status_code == 401


def test_logout_clears_the_session(client):
    client.post(
        "/login",
        data={"username": "testadmin", "password": "correct-horse"}
    )
    assert client.get("/protected-page").status_code == 200

    logout_response = client.get("/logout", follow_redirects=False)
    assert logout_response.status_code == 303
    assert logout_response.headers["location"] == "/login"

    protected = client.get(
        "/protected-page", headers={"accept": "application/json"}
    )
    assert protected.status_code == 401


# ---------------------------------------------------------------------
# auth.py - enforce_tenant_access() / enforce_tenant_access_for_customer()
# ---------------------------------------------------------------------

def test_enforce_tenant_access_allows_admin_for_any_user_id():
    request = FakeRequest({"role": "admin"})
    enforce_tenant_access(request, "some_other_business")  # must not raise


def test_enforce_tenant_access_allows_business_owner_for_their_own_user_id():
    request = FakeRequest({"role": "business_owner", "user_id": "biz1"})
    enforce_tenant_access(request, "biz1")  # must not raise


def test_enforce_tenant_access_blocks_business_owner_for_another_user_id():
    from fastapi import HTTPException

    request = FakeRequest({"role": "business_owner", "user_id": "biz1"})

    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_access(request, "biz2")

    assert exc_info.value.status_code == 403


def test_enforce_tenant_access_blocks_unauthenticated_session():
    from fastapi import HTTPException

    request = FakeRequest({})

    with pytest.raises(HTTPException) as exc_info:
        enforce_tenant_access(request, "biz1")

    assert exc_info.value.status_code == 403


def test_enforce_tenant_access_for_customer_allows_admin(isolated_db):
    request = FakeRequest({"role": "admin"})
    asyncio.run(
        enforce_tenant_access_for_customer(request, "+919900000001")
    )  # must not raise


def test_enforce_tenant_access_for_customer_allows_owning_business(isolated_db):
    register_business("biz1", "+10000000001")
    save_mapping("+919900000001", "+10000000001")

    request = FakeRequest({"role": "business_owner", "user_id": "biz1"})
    asyncio.run(
        enforce_tenant_access_for_customer(request, "+919900000001")
    )  # must not raise


def test_enforce_tenant_access_for_customer_blocks_other_business(isolated_db):
    from fastapi import HTTPException

    register_business("biz1", "+10000000001")
    save_mapping("+919900000001", "+10000000001")

    # biz2 is a real, different business - it must not be able to reach
    # a customer that belongs to biz1.
    request = FakeRequest({"role": "business_owner", "user_id": "biz2"})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(enforce_tenant_access_for_customer(request, "+919900000001"))

    assert exc_info.value.status_code == 403


def test_enforce_tenant_access_for_customer_blocks_unknown_phone(isolated_db):
    from fastapi import HTTPException

    request = FakeRequest({"role": "business_owner", "user_id": "biz1"})

    with pytest.raises(HTTPException) as exc_info:
        asyncio.run(enforce_tenant_access_for_customer(request, "+919900000099"))

    assert exc_info.value.status_code == 403


# ---------------------------------------------------------------------
# auth.py - resolve_dashboard_user_id()
# ---------------------------------------------------------------------

def test_resolve_dashboard_user_id_for_business_owner_is_always_their_own():
    request = FakeRequest({"role": "business_owner", "user_id": "biz1"})
    request.query_params = {}

    assert asyncio.run(resolve_dashboard_user_id(request)) == "biz1"


def test_resolve_dashboard_user_id_for_admin_uses_query_param_and_remembers_it(isolated_db):
    request = FakeRequest({"role": "admin"})
    request.query_params = {"business": "biz1"}

    assert asyncio.run(resolve_dashboard_user_id(request)) == "biz1"
    assert request.session["viewing_user_id"] == "biz1"

    # A later request with no ?business= falls back to what was
    # remembered above, rather than re-defaulting.
    request2 = FakeRequest({"role": "admin", "viewing_user_id": "biz1"})
    request2.query_params = {}

    assert asyncio.run(resolve_dashboard_user_id(request2)) == "biz1"


def test_resolve_dashboard_user_id_for_admin_defaults_to_first_active_business(isolated_db):
    register_business("biz1", "+10000000001")
    set_business_status("biz1", "active")

    request = FakeRequest({"role": "admin"})
    request.query_params = {}

    assert asyncio.run(resolve_dashboard_user_id(request)) == "biz1"


def test_resolve_dashboard_user_id_for_admin_with_no_businesses_is_none(isolated_db):
    request = FakeRequest({"role": "admin"})
    request.query_params = {}

    assert asyncio.run(resolve_dashboard_user_id(request)) is None


# ---------------------------------------------------------------------
# Business-owner login - end-to-end via the minimal test app
# ---------------------------------------------------------------------
# verify.send_otp()/check_otp() are monkeypatched at their import site in
# api/auth.py, so these never call the real Twilio Verify API.

@pytest.fixture
def business(isolated_db):
    """
    One active, registered business with an owner phone number - the
    only kind of business business-login can succeed for (see
    crm.customer_mapping.get_business_by_owner_number()).
    """
    register_business(
        "bizowner1", "+10000000001", owner_whatsapp_number="+919876500000"
    )
    set_business_status("bizowner1", "active")
    return {"user_id": "bizowner1", "phone": "+919876500000"}


def test_business_login_page_loads(client, business):
    response = client.get("/business-login")
    assert response.status_code == 200
    assert "WhatsApp Number" in response.text


def test_business_login_rejects_number_without_plus(client, business):
    response = client.post(
        "/business-login",
        data={"phone": "919876500000"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=format" in response.headers["location"]


def test_business_login_rejects_unregistered_number(client, business, monkeypatch):
    sent = []
    monkeypatch.setattr("api.auth.send_otp", lambda phone, channel=None: sent.append(phone) or True)

    response = client.post(
        "/business-login",
        data={"phone": "+910000000000"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=notfound" in response.headers["location"]
    assert sent == []  # no OTP should be sent for an unknown number


def test_business_login_sends_otp_for_registered_active_business(client, business, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "api.auth.send_otp",
        lambda phone, channel=None: sent.append(phone) or True
    )

    response = client.post(
        "/business-login",
        data={"phone": business["phone"]},
        follow_redirects=False
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/business-login/verify"
    assert sent == [business["phone"]]


def test_business_login_otp_send_rate_limited_after_too_many_requests(client, business, monkeypatch):
    sent = []
    monkeypatch.setattr(
        "api.auth.send_otp",
        lambda phone, channel=None: sent.append(phone) or True
    )

    for _ in range(3):
        client.post("/business-login", data={"phone": business["phone"]})

    response = client.post(
        "/business-login",
        data={"phone": business["phone"]},
        follow_redirects=False
    )
    assert response.headers["location"] == "/business-login?error=ratelimited"
    assert len(sent) == 3  # the 4th request never reached send_otp


def test_business_login_verify_rate_limited_after_too_many_wrong_codes(client, business, monkeypatch):
    monkeypatch.setattr("api.auth.send_otp", lambda phone, channel=None: True)
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: False)

    client.post("/business-login", data={"phone": business["phone"]})

    for _ in range(5):
        response = client.post(
            "/business-login/verify",
            data={"code": "000000"},
            follow_redirects=False
        )
        assert "error=1" in response.headers["location"]

    response = client.post(
        "/business-login/verify",
        data={"code": "000000"},
        follow_redirects=False
    )
    assert response.headers["location"] == "/business-login/verify?error=ratelimited"


def test_business_login_verify_page_redirects_without_a_pending_login(client, business):
    response = client.get("/business-login/verify", follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/business-login"


def test_business_login_verify_wrong_code_shows_error(client, business, monkeypatch):
    monkeypatch.setattr("api.auth.send_otp", lambda phone, channel=None: True)
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: False)

    client.post("/business-login", data={"phone": business["phone"]})

    response = client.post(
        "/business-login/verify",
        data={"code": "000000"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert "error=1" in response.headers["location"]

    # Still not authenticated.
    assert client.get(
        "/protected-page", headers={"accept": "application/json"}
    ).status_code == 401


def test_business_login_verify_correct_code_grants_access(client, business, monkeypatch):
    monkeypatch.setattr("api.auth.send_otp", lambda phone, channel=None: True)
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: code == "123456")

    client.post("/business-login", data={"phone": business["phone"]})

    response = client.post(
        "/business-login/verify",
        data={"code": "123456"},
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/"

    protected = client.get("/protected-page")
    assert protected.status_code == 200


def test_business_owner_session_cannot_reach_businesses_page(client, business, monkeypatch):
    monkeypatch.setattr("api.auth.send_otp", lambda phone, channel=None: True)
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: True)

    client.post("/business-login", data={"phone": business["phone"]})
    client.post("/business-login/verify", data={"code": "123456"})

    # A real browser page load (text/html) redirects away rather than
    # 403ing, per middleware.py's ADMIN_ONLY_PREFIXES handling.
    response = client.get(
        "/businesses", headers={"accept": "text/html"}, follow_redirects=False
    )
    assert response.status_code == 302
    assert response.headers["location"] == "/"

    # A fetch()-style call (no text/html Accept) gets a 403 instead.
    response = client.get(
        "/businesses", headers={"accept": "application/json"}
    )
    assert response.status_code == 403


def test_admin_session_can_still_reach_businesses_page(client):
    client.post(
        "/login",
        data={"username": "testadmin", "password": "correct-horse"}
    )

    response = client.get("/businesses")
    assert response.status_code == 200


def test_business_login_switch_link_present_on_admin_login_page(client):
    response = client.get("/login")
    assert "/business-login" in response.text


def test_business_login_also_works_with_the_business_whatsapp_number(client, business, monkeypatch):
    # A business isn't required to have a separate personal
    # owner_whatsapp_number - logging in with the bot's own WhatsApp
    # number (the one registered as whatsapp_number) must work too.
    sent = []
    monkeypatch.setattr(
        "api.auth.send_otp",
        lambda phone, channel=None: sent.append(phone) or True
    )
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: True)

    response = client.post(
        "/business-login",
        data={"phone": "+10000000001"},  # the bot's own number, not business["phone"]
        follow_redirects=False
    )
    assert response.status_code == 303
    assert response.headers["location"] == "/business-login/verify"
    assert sent == ["+10000000001"]

    client.post("/business-login/verify", data={"code": "123456"})

    protected = client.get("/protected-page")
    assert protected.status_code == 200


# ---------------------------------------------------------------------
# middleware.py - Cache-Control: no-store on every authenticated response
#
# Regression: session-scoped pages (dashboard, settings, follow-ups...)
# bake the current session's business id directly into the HTML (e.g.
# dashboard.html's hidden #userId input). Without no-store, a browser can
# replay a cached copy of that HTML after the session changes - an admin
# switches which business they're viewing, or a different business owner
# logs in on the same browser - so the page's own JS ends up calling
# APIs scoped to a business the *current* session doesn't own. This
# reproduced live as automation/rules/<stale business id> returning 403
# right after a fresh, correct login, because the HTML shell itself was
# served from cache with the previous session's id already baked in.
# ---------------------------------------------------------------------

def test_admin_authenticated_response_is_not_cached(client):
    client.post(
        "/login",
        data={"username": "testadmin", "password": "correct-horse"}
    )

    response = client.get("/protected-page")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_business_owner_authenticated_response_is_not_cached(client, business, monkeypatch):
    monkeypatch.setattr(
        "api.auth.send_otp", lambda phone, channel=None: True
    )
    monkeypatch.setattr("api.auth.check_otp", lambda phone, code: True)

    client.post("/business-login", data={"phone": business["phone"]})
    client.post("/business-login/verify", data={"code": "123456"})

    response = client.get("/protected-page")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"


def test_unauthenticated_response_has_no_forced_cache_header(client):
    # /login itself is on the exempt list (no session to scope it by),
    # so no-store isn't applied there - nothing session-specific to leak.
    response = client.get("/login")
    assert "cache-control" not in {k.lower() for k in response.headers.keys()}
