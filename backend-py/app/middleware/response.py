import json

from fastapi import Request
from fastapi.responses import JSONResponse, Response


def _copy_cors_headers(original_headers, new_headers: dict):
    for key, value in original_headers.items():
        low = key.lower()
        if low.startswith("access-control-") or low in ("vary",):
            new_headers[key] = value


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

    cors_headers = {}
    _copy_cors_headers(response.headers, cors_headers)

    if 200 <= response.status_code < 300:
        wrapped = {"success": True, "data": data, "message": "ok", "error": None}
    else:
        detail = data.get("detail", "Unknown error")
        if isinstance(detail, dict):
            error_code = detail.get("code", "ERROR")
            error_msg = detail.get("message", str(detail))
        elif isinstance(detail, str):
            error_code = detail if detail.isupper() and "_" in detail else "ERROR"
            error_msg = detail
        else:
            error_code = "ERROR"
            error_msg = str(detail)
        wrapped = {
            "success": False,
            "data": None,
            "message": error_msg,
            "error": {"code": error_code, "details": data},
        }

    headers = {"content-type": "application/json"}
    headers.update(cors_headers)
    return JSONResponse(content=wrapped, status_code=response.status_code, headers=headers)
