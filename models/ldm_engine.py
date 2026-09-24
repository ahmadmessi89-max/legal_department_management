# -*- coding: utf-8 -*-
"""A trusted-caller marker that the workflow can set and a client cannot forge.

Some fields must only ever change through the workflow: the approval decision on
a matter (who approved, when), a registered letter's number, a revoked power of
attorney. Signalling "this write is the workflow" with a context key is unsafe,
because Odoo applies a client-supplied ``context`` verbatim on every RPC call, so
anyone who knows the key walks through the guard.

The marker here is process-local and never serialised, so no RPC payload can
reach it. Workflow methods wrap their privileged write in ``engine_guard()``;
the models' ``write`` asks ``in_engine()``. It is thread-local and
depth-counted, so nested workflow calls and concurrent workers stay correct.

Ported from the owner's ``legal_core/models/legal_engine.py``.
"""

import threading
from contextlib import contextmanager

_state = threading.local()


def in_engine():
    """True only while a call is running inside :func:`engine_guard`."""
    return getattr(_state, "depth", 0) > 0


@contextmanager
def engine_guard():
    """Mark the current call as a trusted workflow write for its duration."""
    _state.depth = getattr(_state, "depth", 0) + 1
    try:
        yield
    finally:
        _state.depth = max(0, getattr(_state, "depth", 1) - 1)
