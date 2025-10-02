# Lightweight fallback shim for Hypothesis when not installed.
# Provides minimal no-op decorators and simple strategies sufficient for tests to import and run.
from __future__ import annotations
from typing import Callable, Any, Dict

class _Strategy:
    def __init__(self, sampler: Callable[[], Any]):
        self._sampler = sampler
    def example(self) -> Any:
        return self._sampler()

# strategies submodule facade
class _StrategiesModule:
    def integers(self, min_value: int | None = None, max_value: int | None = None) -> _Strategy:
        # Return a boundary example (min if provided, else 0)
        def _sample() -> int:
            if min_value is not None:
                return int(min_value)
            if max_value is not None:
                return int(max_value)
            return 0
        return _Strategy(_sample)

    def sampled_from(self, items: list[Any] | tuple[Any, ...]) -> _Strategy:
        def _sample() -> Any:
            return items[0] if items else None
        return _Strategy(_sample)

    def builds(self, fn: Callable[..., Any], *args: _Strategy) -> _Strategy:
        def _sample() -> Any:
            vals = [a.example() for a in args]
            return fn(*vals)
        return _Strategy(_sample)

strategies = st = _StrategiesModule()

# No-op settings decorator
def settings(*args, **kwargs):
    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        return func
    # Allow use as @settings(...) or direct call settings(func)
    if args and callable(args[0]) and len(args) == 1 and not kwargs:
        return _decorator(args[0])
    return _decorator

# given decorator that invokes the test once with boundary examples
def given(**given_strategies: Dict[str, _Strategy]):
    def _decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        def _wrapped(*args, **kwargs):
            # Build concrete kwargs from strategies' examples
            bound = {k: (v.example() if isinstance(v, _Strategy) else v) for k, v in given_strategies.items()}
            return func(*args, **bound, **kwargs)
        _wrapped.__name__ = getattr(func, "__name__", "wrapped")
        _wrapped.__doc__ = getattr(func, "__doc__", None)
        return _wrapped
    return _decorator
