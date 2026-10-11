from typing import Optional, Dict, Any
from fastapi import Request
from starlette.templating import Jinja2Templates

templates = Jinja2Templates(directory="templates")


def render_template(
    request: Request,
    name: str,
    context: Optional[Dict[str, Any]] = None,
    status_code: int = 200
):
    ctx = context or {}
    return templates.TemplateResponse(
        request=request,
        name=name,
        context=ctx,
        status_code=status_code
    )
