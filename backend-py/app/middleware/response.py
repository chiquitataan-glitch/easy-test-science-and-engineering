import json

from fastapi import Request
from fastapi.responses import JSONResponse, Response


async def response_wrapper(request: Request, call_next):
    response = await call_next(request)

    content_type = response.headers.get("content-type", "")
    if "application/json" not in content_type:
        return response

    body = b""
    async for chunk in response.body_iterator:
        body += chunk

    try:
        data = json.loads(body)
    except json.JSONDecodeError:
        return Response(
            content=body,
            status_code=response.status_code,
            headers=dict(response.headers),
            media_type=response.media_type,
        )

    if 200 <= response.status_code < 300:
        wrapped = {"success": True, "data": data, "message": "ok", "error": None}
    else:
        detail = data.get("detail", "Unknown error")
        wrapped = {
            "success": False,
            "data": None,
            "message": detail if isinstance(detail, str) else str(detail),
            "error": {"code": "ERROR", "details": data},
        }

    return JSONResponse(content=wrapped, status_code=response.status_code)
