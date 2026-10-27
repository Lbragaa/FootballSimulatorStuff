"""Scoped forward calculations are separate from development profile packages."""

from contextlib import contextmanager
from contextvars import ContextVar
from . import SCOPE

_scope = ContextVar("authorized_forward_scope", default=None)
REHEARSAL = "NONCANONICAL FORWARD AUTHORIZATION REHEARSAL"
FORWARD = "UNACCEPTED OFFICIAL FORWARD CANDIDATE"


def current():
    return _scope.get() or SCOPE


def save_profile():
    if current() == REHEARSAL:
        return "FORWARD-CALCULATION-TEST-1"
    if current() == FORWARD:
        return "FORWARD-CALCULATION-1"
    return "DEV-03C"


@contextmanager
def calculation(test_only):
    token = _scope.set(REHEARSAL if test_only else FORWARD)
    try:
        yield
    finally:
        _scope.reset(token)
