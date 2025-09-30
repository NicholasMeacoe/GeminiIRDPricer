import React, { useState, useEffect } from 'react';
import './App.css';

const API_BASE_URL = 'http://localhost:8000/api';

interface YieldCurveData {
  "Maturity (Years)": number;
  Rate: number;
  Date: string;
}

interface SwapFormData {
  notional: string;
  fixed_rate: number;
  maturity_date: string;
}

function App() {
  const [yieldCurve, setYieldCurve] = useState<YieldCurveData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  
  const [formData, setFormData] = useState<SwapFormData>({
    notional: '10m',
    fixed_rate: 4.5,
    maturity_date: '5y'
  });

  // Load initial yield curve data
  useEffect(() => {
    const loadYieldCurve = async () => {
      try {
        const response = await fetch(`${API_BASE_URL}/yield-curve`);
        if (!response.ok) throw new Error('Failed to fetch yield curve');
        const data = await response.json();
        setYieldCurve(data.yield_curve);
      } catch (err) {
        setError(`Failed to load yield curve: ${err}`);
      }
    };

    loadYieldCurve();
  }, []);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    setFormData(prev => ({
      ...prev,
      [name]: name === 'fixed_rate' ? parseFloat(value) || 0 : value
    }));
  };

  const handlePriceSwap = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/price-swap`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(formData),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to price swap');
      }
      
      const data = await response.json();
      setResult(`Swap Value: $${data.swap_value.toFixed(2)}`);
      setSuccess('Swap priced successfully!');
    } catch (err) {
      setError(`${err}`);
      setResult(null);
    } finally {
      setLoading(false);
    }
  };

  const handleSolveParRate = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    
    try {
      const response = await fetch(`${API_BASE_URL}/solve-par-rate`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          notional: formData.notional,
          maturity_date: formData.maturity_date
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to solve par rate');
      }
      
      const data = await response.json();
      setFormData(prev => ({ ...prev, fixed_rate: data.par_rate }));
      setSuccess(`Par rate solved: ${data.par_rate.toFixed(4)}%`);
    } catch (err) {
      setError(`${err}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="container">
      <h1>Interest Rate Swap Pricer</h1>
      <p>Price interest rate swaps and solve for par rates using yield curve data</p>

      {/* Alerts */}
      {error && (
        <div className="alert alert-error">
          {error}
          <button onClick={() => setError(null)} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
      )}
      {success && (
        <div className="alert alert-success">
          {success}
          <button onClick={() => setSuccess(null)} style={{ float: 'right', background: 'none', border: 'none', cursor: 'pointer' }}>
            ✕
          </button>
        </div>
      )}

      {/* Pricing Form */}
      <div className="card">
        <h2>Swap Parameters</h2>
        <form>
          <div className="grid">
            <div className="form-group">
              <label className="form-label" htmlFor="notional">Notional</label>
              <input
                type="text"
                id="notional"
                name="notional"
                value={formData.notional}
                onChange={handleInputChange}
                placeholder="e.g., 10m"
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="fixed_rate">Fixed Rate (%)</label>
              <input
                type="number"
                id="fixed_rate"
                name="fixed_rate"
                value={formData.fixed_rate}
                onChange={handleInputChange}
                step="0.01"
                className="form-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="maturity_date">Maturity</label>
              <input
                type="text"
                id="maturity_date"
                name="maturity_date"
                value={formData.maturity_date}
                onChange={handleInputChange}
                placeholder="e.g., 5y or 2028-12-31"
                className="form-input"
              />
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={handlePriceSwap}
              disabled={loading}
              className="btn btn-primary"
            >
              {loading ? 'Pricing...' : 'Price Swap'}
            </button>

            <button
              type="button"
              onClick={handleSolveParRate}
              disabled={loading}
              className="btn btn-secondary"
            >
              {loading ? 'Solving...' : 'Solve Par Rate'}
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {result && (
        <div className="card">
          <h2>Results</h2>
          <div className="alert alert-success">
            {result}
          </div>
        </div>
      )}

      {/* Yield Curve */}
      <div className="card">
        <h2>Yield Curve Data</h2>
        {yieldCurve.length > 0 ? (
          <table className="table">
            <thead>
              <tr>
                <th>Maturity (Years)</th>
                <th>Rate (%)</th>
                <th>Date</th>
              </tr>
            </thead>
            <tbody>
              {yieldCurve.map((point, index) => (
                <tr key={index}>
                  <td>{point["Maturity (Years)"]}</td>
                  <td className="text-right">{point.Rate.toFixed(4)}</td>
                  <td>{new Date(point.Date).toLocaleDateString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : (
          <p>Loading yield curve data...</p>
        )}
      </div>
    </div>
  );
}

export default App;
