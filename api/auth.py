from fastapi import APIRouter, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates

from auth import verify_admin_login

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
