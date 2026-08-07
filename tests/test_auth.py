"""
Tests for the admin login gate - auth.py's credential check, and the
end-to-end behavior of api/auth.py's login/logout routes plus
middleware.py's AdminAuthMiddleware (session-gates every route except
/login, /logout, /webhook, /health - see main.py for wiring).

The middleware tests build a small standalone FastAPI app (SessionMiddleware
+ AdminAuthMiddleware + api/auth.py + a couple of dummy protected routes)
rather than importing the real main.py, since main.py pulls in
api/webhook.py's RAG chain (langchain_huggingface etc.), which has nothing
to do with auth and isn't otherwise needed here.
"""

import bcrypt
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware

import auth
from auth import verify_admin_login
from api.auth import router as auth_router
from middleware import AdminAuthMiddleware


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
