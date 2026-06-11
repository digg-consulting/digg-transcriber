"""Shared HTTP client and retry helpers."""

import time
from collections.abc import Callable
from typing import TypeVar

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


T = TypeVar("T")

_session: requests.Session | None = None


def get_http_session() -> requests.Session:
    global _session
    if _session is not None:
        return _session

    retry = Retry(
        total=5,
        connect=5,
        read=5,
        backoff_factor=0.5,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=frozenset(["GET", "POST", "HEAD", "OPTIONS"]),
        raise_on_status=False,
    )
    adapter = HTTPAdapter(max_retries=retry, pool_connections=20, pool_maxsize=20)

    session = requests.Session()
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    session.headers.update({"User-Agent": "digg-transcriber/0.1"})
    _session = session
    return session


def retry_call(func: Callable[[], T], attempts: int = 3, base_delay: float = 0.5) -> T:
    last_error: Exception | None = None
    for attempt in range(1, attempts + 1):
        try:
            return func()
        except Exception as exc:
            last_error = exc
            if attempt == attempts:
                break
            time.sleep(base_delay * attempt)
    assert last_error is not None
    raise last_error