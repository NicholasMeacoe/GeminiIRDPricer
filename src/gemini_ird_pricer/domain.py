from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CurvePoint:
    maturity_years: float
    rate: float  # as decimal
    date: datetime


@dataclass(frozen=True)
class Notional:
    amount: float


@dataclass(frozen=True)
class Tenor:
    years: float
