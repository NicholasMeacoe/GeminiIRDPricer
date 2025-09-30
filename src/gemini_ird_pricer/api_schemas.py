from __future__ import annotations
from typing import List, Optional
from pydantic import BaseModel, Field, ValidationError, field_validator


class CurvePoint(BaseModel):
    """Represents a single point on the yield curve."""
    maturity: float = Field(..., description="Maturity in years", gt=0, le=50)
    rate: float = Field(..., description="Rate in percent", ge=-10, le=50)

    @field_validator("maturity")
    @classmethod
    def validate_maturity(cls, v: float) -> float:
        """Validate maturity is within reasonable bounds."""
        if v <= 0:
            raise ValueError("Maturity must be positive")
        if v > 50:
            raise ValueError("Maturity must be 50 years or less")
        return v
    
    @field_validator("rate")
    @classmethod
    def validate_rate(cls, v: float) -> float:
        """Validate rate is within reasonable bounds."""
        if v < -10:
            raise ValueError("Rate cannot be less than -10%")
        if v > 50:
            raise ValueError("Rate cannot be greater than 50%")
        return v


class PriceRequest(BaseModel):
    """Request schema for pricing a swap."""
    notional: str = Field(..., description="Notional amount (e.g., '10m', '1000000')")
    maturity_date: str = Field(..., description="Maturity date (YYYY-MM-DD) or tenor (e.g., '5y')")
    fixed_rate: float = Field(..., description="Fixed rate in percent", ge=-10, le=50)
    curve: Optional[List[CurvePoint]] = Field(None, description="Optional yield curve override", max_length=200)

    @field_validator("notional")
    @classmethod
    def validate_notional(cls, v: str) -> str:
        """Validate notional format."""
        if not v or not v.strip():
            raise ValueError("Notional cannot be empty")
        return v.strip()
    
    @field_validator("maturity_date")
    @classmethod
    def validate_maturity_date(cls, v: str) -> str:
        """Validate maturity date format."""
        if not v or not v.strip():
            raise ValueError("Maturity date cannot be empty")
        return v.strip()
    
    @field_validator("curve")
    @classmethod
    def validate_curve(cls, v: Optional[List[CurvePoint]]) -> Optional[List[CurvePoint]]:
        """Validate curve points."""
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("Curve cannot be empty if provided")
        
        if len(v) > 200:
            raise ValueError("Curve cannot have more than 200 points")
        
        # Check for duplicate maturities
        maturities = [point.maturity for point in v]
        if len(maturities) != len(set(maturities)):
            raise ValueError("Curve cannot have duplicate maturities")
        
        # Check maturities are sorted
        if maturities != sorted(maturities):
            raise ValueError("Curve maturities must be in ascending order")
        
        return v


class SolveRequest(BaseModel):
    """Request schema for solving par rate."""
    notional: str = Field(..., description="Notional amount (e.g., '10m', '1000000')")
    maturity_date: str = Field(..., description="Maturity date (YYYY-MM-DD) or tenor (e.g., '5y')")
    curve: Optional[List[CurvePoint]] = Field(None, description="Optional yield curve override", max_length=200)

    @field_validator("notional")
    @classmethod
    def validate_notional(cls, v: str) -> str:
        """Validate notional format."""
        if not v or not v.strip():
            raise ValueError("Notional cannot be empty")
        return v.strip()
    
    @field_validator("maturity_date")
    @classmethod
    def validate_maturity_date(cls, v: str) -> str:
        """Validate maturity date format."""
        if not v or not v.strip():
            raise ValueError("Maturity date cannot be empty")
        return v.strip()
    
    @field_validator("curve")
    @classmethod
    def validate_curve(cls, v: Optional[List[CurvePoint]]) -> Optional[List[CurvePoint]]:
        """Validate curve points."""
        if v is None:
            return v
        
        if len(v) == 0:
            raise ValueError("Curve cannot be empty if provided")
        
        if len(v) > 200:
            raise ValueError("Curve cannot have more than 200 points")
        
        # Check for duplicate maturities
        maturities = [point.maturity for point in v]
        if len(maturities) != len(set(maturities)):
            raise ValueError("Curve cannot have duplicate maturities")
        
        # Check maturities are sorted
        if maturities != sorted(maturities):
            raise ValueError("Curve maturities must be in ascending order")
        
        return v


class PriceResult(BaseModel):
    """Result schema for pricing response."""
    npv: float = Field(..., description="Net present value")
    schedule: list[dict] = Field(..., description="Payment schedule")


class PriceResponse(BaseModel):
    """Response schema for pricing endpoint."""
    result: PriceResult


class SolveResult(BaseModel):
    """Result schema for solve response."""
    par_rate_percent: float = Field(..., description="Par rate in percent")


class SolveResponse(BaseModel):
    """Response schema for solve endpoint."""
    result: SolveResult
