"""Tests for enhanced API validation."""

import pytest
from pydantic import ValidationError
from src.gemini_ird_pricer.api_schemas import CurvePoint, PriceRequest, SolveRequest


class TestCurvePoint:
    """Test CurvePoint validation."""
    
    def test_valid_curve_point(self):
        """Test valid curve point creation."""
        point = CurvePoint(maturity=5.0, rate=3.5)
        assert point.maturity == 5.0
        assert point.rate == 3.5
    
    def test_negative_maturity(self):
        """Test negative maturity validation."""
        with pytest.raises(ValidationError) as exc_info:
            CurvePoint(maturity=-1.0, rate=3.5)
        
        errors = exc_info.value.errors()
        # Check for either custom validator message or Pydantic constraint message
        assert any("positive" in str(error).lower() or "greater than 0" in str(error) for error in errors)
    
    def test_zero_maturity(self):
        """Test zero maturity validation."""
        with pytest.raises(ValidationError) as exc_info:
            CurvePoint(maturity=0.0, rate=3.5)
        
        errors = exc_info.value.errors()
        assert any("greater than 0" in str(error) for error in errors)
    
    def test_high_maturity(self):
        """Test high maturity validation."""
        with pytest.raises(ValidationError) as exc_info:
            CurvePoint(maturity=100.0, rate=3.5)
        
        errors = exc_info.value.errors()
        # Check for either custom validator message or Pydantic constraint message
        assert any("50" in str(error) and ("less" in str(error) or "equal" in str(error)) for error in errors)
    
    def test_low_rate(self):
        """Test low rate validation."""
        with pytest.raises(ValidationError) as exc_info:
            CurvePoint(maturity=5.0, rate=-15.0)
        
        errors = exc_info.value.errors()
        # Check for either custom validator message or Pydantic constraint message
        assert any("-10" in str(error) or "greater than or equal to -10" in str(error) for error in errors)
    
    def test_high_rate(self):
        """Test high rate validation."""
        with pytest.raises(ValidationError) as exc_info:
            CurvePoint(maturity=5.0, rate=60.0)
        
        errors = exc_info.value.errors()
        # Check for either custom validator message or Pydantic constraint message
        assert any("50" in str(error) and ("less" in str(error) or "equal" in str(error)) for error in errors)


class TestPriceRequest:
    """Test PriceRequest validation."""
    
    def test_valid_price_request(self):
        """Test valid price request creation."""
        request = PriceRequest(
            notional="10m",
            maturity_date="5y",
            fixed_rate=4.5
        )
        assert request.notional == "10m"
        assert request.maturity_date == "5y"
        assert request.fixed_rate == 4.5
    
    def test_empty_notional(self):
        """Test empty notional validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="",
                maturity_date="5y",
                fixed_rate=4.5
            )
        
        errors = exc_info.value.errors()
        assert any("cannot be empty" in str(error) for error in errors)
    
    def test_empty_maturity_date(self):
        """Test empty maturity date validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="",
                fixed_rate=4.5
            )
        
        errors = exc_info.value.errors()
        assert any("cannot be empty" in str(error) for error in errors)
    
    def test_high_fixed_rate(self):
        """Test high fixed rate validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="5y",
                fixed_rate=60.0
            )
        
        errors = exc_info.value.errors()
        assert any("less than or equal to 50" in str(error) for error in errors)
    
    def test_valid_curve_override(self):
        """Test valid curve override."""
        curve = [
            CurvePoint(maturity=1.0, rate=2.0),
            CurvePoint(maturity=5.0, rate=3.0),
            CurvePoint(maturity=10.0, rate=4.0)
        ]
        request = PriceRequest(
            notional="10m",
            maturity_date="5y",
            fixed_rate=4.5,
            curve=curve
        )
        assert len(request.curve) == 3
    
    def test_empty_curve_override(self):
        """Test empty curve override validation."""
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="5y",
                fixed_rate=4.5,
                curve=[]
            )
        
        errors = exc_info.value.errors()
        assert any("cannot be empty if provided" in str(error) for error in errors)
    
    def test_duplicate_maturities(self):
        """Test duplicate maturities validation."""
        curve = [
            CurvePoint(maturity=5.0, rate=2.0),
            CurvePoint(maturity=5.0, rate=3.0)  # Duplicate maturity
        ]
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="5y",
                fixed_rate=4.5,
                curve=curve
            )
        
        errors = exc_info.value.errors()
        assert any("duplicate maturities" in str(error) for error in errors)
    
    def test_unsorted_maturities(self):
        """Test unsorted maturities validation."""
        curve = [
            CurvePoint(maturity=10.0, rate=4.0),
            CurvePoint(maturity=5.0, rate=3.0)  # Out of order
        ]
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="5y",
                fixed_rate=4.5,
                curve=curve
            )
        
        errors = exc_info.value.errors()
        assert any("ascending order" in str(error) for error in errors)
    
    def test_too_many_curve_points(self):
        """Test too many curve points validation."""
        # Create 201 points with valid maturities (within 50 year limit)
        curve = [CurvePoint(maturity=float(i)/10, rate=3.0) for i in range(1, 202)]  # 0.1 to 20.1 years
        with pytest.raises(ValidationError) as exc_info:
            PriceRequest(
                notional="10m",
                maturity_date="5y",
                fixed_rate=4.5,
                curve=curve
            )
        
        errors = exc_info.value.errors()
        assert any("200" in str(error) for error in errors)


class TestSolveRequest:
    """Test SolveRequest validation."""
    
    def test_valid_solve_request(self):
        """Test valid solve request creation."""
        request = SolveRequest(
            notional="10m",
            maturity_date="5y"
        )
        assert request.notional == "10m"
        assert request.maturity_date == "5y"
    
    def test_solve_request_with_curve(self):
        """Test solve request with curve override."""
        curve = [
            CurvePoint(maturity=1.0, rate=2.0),
            CurvePoint(maturity=5.0, rate=3.0)
        ]
        request = SolveRequest(
            notional="10m",
            maturity_date="5y",
            curve=curve
        )
        assert len(request.curve) == 2
    
    def test_solve_request_validation_same_as_price(self):
        """Test that SolveRequest has same validation as PriceRequest for common fields."""
        # Empty notional should fail
        with pytest.raises(ValidationError):
            SolveRequest(notional="", maturity_date="5y")
        
        # Empty maturity date should fail
        with pytest.raises(ValidationError):
            SolveRequest(notional="10m", maturity_date="")
        
        # Invalid curve should fail
        with pytest.raises(ValidationError):
            SolveRequest(
                notional="10m",
                maturity_date="5y",
                curve=[]
            )
