import logging

from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import verify_admin_login
from crm.customer_mapping import get_business_by_login_number
from verify import VerifyNotConfigured, check_otp, send_otp

logger = logging.getLogger(__name__)

router = APIRouter()

templates = Jinja2Templates(directory="templates")


@router.get("/login")
async def login_page(request: Request):

    # AdminAuthMiddleware redirects here with ?error=1 after a failed
    # attempt (PRG pattern - the POST below redirects rather than
    # rendering directly, so refreshing the page after a failed login
    # doesn't resubmit the credentials).
    return templates.TemplateResponse(
        request=request,
        name="login.html",
        context={
            "error": request.query_params.get("error") == "1"
        }
    )


@router.post("/login")
async def login_submit(request: Request):

    form = await request.form()

    username = (form.get("username") or "").strip()
    password = form.get("password") or ""

    valid = await run_in_threadpool(
        verify_admin_login, username, password
    )

    if not valid:
        return RedirectResponse(
            url="/login?error=1",
            status_code=303
        )

    request.session["role"] = "admin"
    request.session["username"] = username

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):

    request.session.clear()

    return RedirectResponse(url="/login", status_code=303)


# ==========================================================
# Business-owner login (WhatsApp/SMS OTP via Twilio Verify)
# ==========================================================
# Two-step PRG flow, same pattern as admin login above:
#   1. GET/POST /business-login        - owner enters their phone number
#   2. GET/POST /business-login/verify - owner enters the code they got
#
# The phone number being verified lives in request.session (not a
# hidden form field) between steps 1 and 2, so step 2 can't be reached
# with an arbitrary phone number that was never actually sent a code.


@router.get("/business-login")
async def business_login_page(request: Request):

    return templates.TemplateResponse(
        request=request,
        name="business_login.html",
        context={
            "error": request.query_params.get("error"),
        }
    )


@router.post("/business-login")
async def business_login_submit(request: Request):

    form = await request.form()

    phone = (form.get("phone") or "").strip()

    if not phone.startswith("+"):
        return RedirectResponse(
            url="/business-login?error=format",
            status_code=303
        )

    business = await run_in_threadpool(get_business_by_login_number, phone)

    if not business:
        # Deliberately vague - doesn't reveal whether this number
        # belongs to an inactive/unregistered business vs. a typo.
        return RedirectResponse(
            url="/business-login?error=notfound",
            status_code=303
        )

    try:
        await run_in_threadpool(send_otp, phone)
    except VerifyNotConfigured:
        logger.error("Business login attempted but Verify isn't configured")
        return RedirectResponse(
            url="/business-login?error=unavailable",
            status_code=303
        )
    except Exception:
        logger.exception("Failed to send OTP to %s", phone)
        return RedirectResponse(
            url="/business-login?error=send_failed",
            status_code=303
        )

    request.session["otp_pending_phone"] = phone
    request.session["otp_pending_user_id"] = business["user_id"]

    return RedirectResponse(url="/business-login/verify", status_code=303)


@router.get("/business-login/verify")
async def business_login_verify_page(request: Request):

    if not request.session.get("otp_pending_phone"):
        return RedirectResponse(url="/business-login", status_code=303)

    return templates.TemplateResponse(
        request=request,
        name="business_login_verify.html",
        context={
            "phone": request.session["otp_pending_phone"],
            "error": request.query_params.get("error") == "1",
        }
    )


@router.post("/business-login/verify")
async def business_login_verify_submit(request: Request):

    phone = request.session.get("otp_pending_phone")
    user_id = request.session.get("otp_pending_user_id")

    if not phone or not user_id:
        return RedirectResponse(url="/business-login", status_code=303)

    form = await request.form()
    code = (form.get("code") or "").strip()

    try:
        valid = await run_in_threadpool(check_otp, phone, code)
    except VerifyNotConfigured:
        logger.error("Business login verify attempted but Verify isn't configured")
        return RedirectResponse(
            url="/business-login?error=unavailable",
            status_code=303
        )

    if not valid:
        return RedirectResponse(
            url="/business-login/verify?error=1",
            status_code=303
        )

    # Re-check the business is still active (rather than trusting the
    # values stashed at step 1) - covers the edge case of an admin
    # deactivating this business in the window between sending the code
    # and it being verified.
    business = await run_in_threadpool(get_business_by_login_number, phone)

    if not business:
        request.session.pop("otp_pending_phone", None)
        request.session.pop("otp_pending_user_id", None)
        return RedirectResponse(
            url="/business-login?error=notfound",
            status_code=303
        )

    request.session.pop("otp_pending_phone", None)
    request.session.pop("otp_pending_user_id", None)

    request.session["role"] = "business_owner"
    request.session["user_id"] = business["user_id"]
    request.session["business_id"] = business["business_id"]

    return RedirectResponse(url="/", status_code=303)
