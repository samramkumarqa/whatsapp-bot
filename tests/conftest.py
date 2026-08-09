import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import pytest

import database.db as db


@pytest.fixture
def isolated_db(tmp_path, monkeypatch):
    """
    Every CRM/automation function in this codebase resolves its DB path
    relative to the process's current working directory (e.g. "data/app.db",
    "conversations.db" in database/db.py). This fixture chdir's into a
    throwaway directory per test and resets the connection pools in
    database/db.py so no pooled connection from a previous test - or from
    the real project directory - leaks into the test. It then runs the
    actual schema-init functions from each module, so tests exercise the
    real schema rather than a hand-rolled mock one.
    """

    monkeypatch.chdir(tmp_path)
    os.makedirs("data", exist_ok=True)

    # Jinja2Templates(directory="templates") (api/auth.py, api/misc.py,
    # etc.) resolves that path relative to cwd at render time, not at
    # import time - symlinking the real templates/ dir into the
    # throwaway cwd lets tests that render a page (e.g. business-login)
    # still find it after the chdir above, without duplicating the
    # actual template files anywhere.
    if not os.path.exists("templates"):
        os.symlink(
            os.path.join(PROJECT_ROOT, "templates"),
            "templates"
        )

    # Fresh pools pointing at the new cwd. The pools created at import time
    # (in the real project directory) may already hold open connections to
    # a totally different set of files.
    monkeypatch.setattr(db, "_crm_pool", db._ConnectionPool(db.CRM_DB))
    monkeypatch.setattr(
        db, "_conversation_pool", db._ConnectionPool(db.CONVERSATION_DB)
    )

    from crm.customer_mapping import (
        init_customer_mapping,
        init_business_settings,
    )
    from crm.lead_manager import init_leads
    from crm.opportunity_manager import init_opportunities
    from crm.tag_manager import init_tags
    from crm.activity_manager import init_activity
    from crm.followup_manager import init_followups
    from reminder_manager import init_reminders
    from conversations import init_db as init_conversations
    from unread_manager import init_unread
    from automation.database import init_automation_db
    from automation.rule_stats import init_rule_executions

    init_customer_mapping()
    init_business_settings()
    init_leads()
    init_opportunities()
    init_tags()
    init_activity()
    init_followups()
    init_reminders()
    init_conversations()
    init_unread()
    init_automation_db()
    init_rule_executions()

    yield


class FakeRequest:
    """
    Minimal stand-in for a Starlette Request. auth.enforce_tenant_access()
    and enforce_tenant_access_for_customer() only ever read
    request.session, so tests that call route handler functions directly
    (bypassing the real ASGI app/middleware) can pass one of these
    instead of spinning up a real request with a signed session cookie.
    """

    def __init__(self, session=None):
        self.session = session or {}


@pytest.fixture
def admin_request():
    """
    A FakeRequest with an admin session - admin bypasses
    enforce_tenant_access()'s business-ownership check entirely, so this
    is the right stand-in for tests that aren't specifically about
    tenant isolation (see tests/test_tenant_isolation.py for those).
    """
    return FakeRequest({"role": "admin"})


def business_owner_request(user_id):
    """
    A FakeRequest for a business_owner session scoped to `user_id` - for
    tests that specifically exercise the business-owner access path
    (e.g. confirming a business owner can reach their own data but not
    another business's).
    """
    return FakeRequest({"role": "business_owner", "user_id": user_id})
