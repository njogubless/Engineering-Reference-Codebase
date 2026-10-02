from collections.abc import Callable

from django.http import HttpRequest, HttpResponse

from apps.core.request_context import REQUEST_ID_HEADER, request_id_var, resolve_request_id


class RequestIdMiddleware:
    """Accepts or generates `X-Request-ID`, exposes it to logs, and echoes it back.

    The same ID is returned in every Problem Details body, so a user-reported
    error can be traced to the exact log lines that produced it.
    """

    def __init__(self, get_response: Callable[[HttpRequest], HttpResponse]) -> None:
        self.get_response = get_response

    def __call__(self, request: HttpRequest) -> HttpResponse:
        request_id = resolve_request_id(request.headers.get(REQUEST_ID_HEADER))
        token = request_id_var.set(request_id)
        try:
            response = self.get_response(request)
        finally:
            # Always reset: a leaked value would tag another request's logs.
            request_id_var.reset(token)
        response[REQUEST_ID_HEADER] = request_id
        return response
