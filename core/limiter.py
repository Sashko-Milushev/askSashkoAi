"""
Central slowapi limiter instance.
Import `limiter` wherever rate-limit decorators are needed.
"""
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

