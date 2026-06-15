"""Synchronous handle on the live Axiom Lean Engine (AXLE).

A thin sync wrapper over the official async ``axle.AxleClient``
(``pip install axiom-axle``). The official package is imported lazily inside
``__init__`` so that importing :mod:`falsify` never requires it - only the live
path does. The concurrent Verina audit in :mod:`falsify.live.verina` drives the
async client directly; this wrapper is the convenient general-purpose handle.
"""

from __future__ import annotations

from typing import Optional


class AxleClient:
    """``check`` / ``disprove`` against the live engine.

    Requires an API key (``AXLE_API_KEY`` env var, free key at
    https://axle.axiommath.ai/app/console).
    """

    live = True

    def __init__(self, api_key: Optional[str] = None, url: Optional[str] = None,
                 environment: str = "lean-4.28.0", max_concurrency: int = 8,
                 timeout_seconds: float = 200.0):
        import asyncio
        try:
            import axle as _axle
        except ImportError as e:  # pragma: no cover - live path only
            raise RuntimeError(
                "The live path needs the official client: pip install axiom-axle"
            ) from e
        self._axle = _axle
        self.environment = environment
        self.timeout_seconds = timeout_seconds
        self._loop = asyncio.new_event_loop()
        self._client = self._loop.run_until_complete(
            _axle.AxleClient(api_key=api_key, url=url, max_concurrency=max_concurrency).__aenter__()
        )

    def close(self) -> None:
        try:
            self._loop.run_until_complete(self._client.__aexit__(None, None, None))
        finally:
            self._loop.close()

    def __enter__(self) -> "AxleClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def check(self, content: str, ignore_imports: Optional[bool] = None,
              timeout_seconds: Optional[float] = None):
        return self._loop.run_until_complete(self._client.check(
            content=content, environment=self.environment,
            ignore_imports=ignore_imports,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
        ))

    def disprove(self, content: str, ignore_imports: Optional[bool] = None,
                 timeout_seconds: Optional[float] = None):
        return self._loop.run_until_complete(self._client.disprove(
            content=content, environment=self.environment,
            ignore_imports=ignore_imports,
            timeout_seconds=timeout_seconds or self.timeout_seconds,
        ))
