"""Shared SlowAPI rate limiter instance.

SlowAPI decorators need a single limiter configured on the FastAPI app state and
middleware added in app.main.
"""

from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)
