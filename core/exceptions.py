"""Single error shape for the whole API: {"detail": str, "errors"?: {field: [messages]}}."""

from rest_framework.views import exception_handler


def api_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is None:  # non-API exception → let Django produce a 500
        return None

    data = response.data
    if isinstance(data, dict) and "detail" in data:
        payload = {"detail": str(data["detail"])}
        extra = {k: v for k, v in data.items() if k not in ("detail", "code")}
        if extra:
            payload["errors"] = extra
    elif isinstance(data, dict):
        payload = {"detail": "Validation failed.", "errors": data}
    else:
        payload = {"detail": "Validation failed.", "errors": {"non_field_errors": data}}

    response.data = payload
    return response
