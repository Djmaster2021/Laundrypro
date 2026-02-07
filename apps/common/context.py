from __future__ import annotations

from threading import local

_ctx = local()


def set_current_request(request):
    _ctx.request = request


def get_current_request():
    return getattr(_ctx, "request", None)


def clear_current_request():
    if hasattr(_ctx, "request"):
        delattr(_ctx, "request")
