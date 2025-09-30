import React, { useState, useEffect } from 'react';
import './App.css';
import YieldCurveChart from './components/YieldCurveChart';
import Tabs from './components/Tabs';

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
  direction: 'payer' | 'receiver';
}

function App() {
  const [yieldCurve, setYieldCurve] = useState<YieldCurveData[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [result, setResult] = useState<string | null>(null);
  const [parRate, setParRate] = useState<number | null>(null);
  const [backendConnected, setBackendConnected] = useState(false);
  const [paymentSchedule, setPaymentSchedule] = useState<any[]>([]);
  const [plotData, setPlotData] = useState<any>(null);
  
  // Internationalization
  const [locale, setLocale] = useState<string>('en-US');
  const numberFormatter = React.useMemo(() => new Intl.NumberFormat(locale, { minimumFractionDigits: 2, maximumFractionDigits: 2 }), [locale]);
  const [currency, setCurrency] = useState<string>('USD');
  const currencyFormatter = React.useMemo(() => new Intl.NumberFormat(locale, { style: 'currency', currency, minimumFractionDigits: 2, maximumFractionDigits: 2 }), [locale, currency]);
  const dateFormatter = React.useMemo(() => new Intl.DateTimeFormat(locale), [locale]);

  // UI state for maturity input type and validation messages
  const [maturityInputType, setMaturityInputType] = useState<'tenor' | 'date'>('tenor');
  const [errors, setErrors] = useState<{ [k: string]: string | null }>({});
  const [bdc, setBdc] = useState<string>('None');

  // Local editable yield curve overrides (percent inputs)
  const [curveOverrides, setCurveOverrides] = useState<{ maturity_years: number; rate: number }[]>([]);
  
  const [formData, setFormData] = useState<SwapFormData>({
    notional: '10m',
    fixed_rate: 4.5,
    maturity_date: '5y',
    direction: 'payer'
  });

  // Validation helpers
  const validateNotional = (s: string): string | null => {
    if (!s || !s.trim()) return 'Notional is required.';
    if (!/^\d+\.?\d*\s*([mkbMKBuU$])?$/.test(s.trim())) return 'Invalid notional. Examples: 1000000, 10m, 250k.';
    return null;
  };
  const validateFixedRate = (v: number): string | null => {
    if (!Number.isFinite(v)) return 'Fixed rate must be a number.';
    if (v < -10 || v > 50) return 'Fixed rate must be between -10% and 50%.';
    return null;
  };
  const validateMaturity = (s: string, mode: 'tenor' | 'date'): string | null => {
    if (!s || !s.trim()) return 'Maturity is required.';
    if (mode === 'date') {
      if (!/^\d{4}-\d{2}-\d{2}$/.test(s)) return 'Use YYYY-MM-DD format.';
      const d = new Date(s);
      if (isNaN(d.getTime())) return 'Invalid date.';
      return null;
    } else {
      if (!/^\d+\s*[ymdYMD]$/.test(s.trim())) return 'Use tenor like 5y, 18m, or 30d.';
      return null;
    }
  };

  const isFormValid = React.useMemo(() => {
    return !errors.notional && !errors.fixed_rate && !errors.maturity_date;
  }, [errors]);

  const totals = React.useMemo(() => {
    const agg = paymentSchedule.reduce((acc, p) => {
      acc.fixed += Number(p.pv_fixed || 0);
      acc.floating += Number(p.pv_floating || 0);
      return acc;
    }, { fixed: 0, floating: 0 });
    return {
      pvFixed: agg.fixed,
      pvFloating: agg.floating,
      npv: agg.floating - agg.fixed,
      count: paymentSchedule.length,
    };
  }, [paymentSchedule]);

  // Load initial yield curve data with retry logic
  useEffect(() => {
    const loadYieldCurve = async (retries = 3) => {
      try {
        console.log('Attempting to connect to backend...');
        const response = await fetch(`${API_BASE_URL}/yield-curve`, {
          method: 'GET',
          headers: {
            'Accept': 'application/json',
          },
        });
        
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        setYieldCurve(data.yield_curve);
        setPlotData(data.plot_data);
        setBackendConnected(true);
        console.log('Successfully loaded yield curve data');
      } catch (err) {
        console.error('Failed to load yield curve:', err);
        
        if (retries > 0) {
          console.log(`Retrying in 2 seconds... (${retries} retries left)`);
          setTimeout(() => loadYieldCurve(retries - 1), 2000);
        } else {
          setError(`Failed to connect to backend after multiple attempts. Please ensure the backend server is running on http://localhost:8000. Error: ${err}`);
        }
      }
    };

    loadYieldCurve();
  }, []);

  // Initialize validation on mount
  useEffect(() => {
    setErrors({
      notional: validateNotional(formData.notional),
      fixed_rate: validateFixedRate(formData.fixed_rate),
      maturity_date: validateMaturity(formData.maturity_date, maturityInputType),
    });
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Re-validate maturity when input mode changes
  useEffect(() => {
    setErrors(prev => ({
      ...prev,
      maturity_date: validateMaturity(formData.maturity_date, maturityInputType),
    }));
  }, [maturityInputType, formData.maturity_date]);

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    const processed = name === 'fixed_rate' ? (parseFloat(value) || 0) : (name === 'direction' ? (value as 'payer' | 'receiver') : value);
    setFormData(prev => ({ ...prev, [name]: processed as any }));

    // Field-level validation
    setErrors(prev => {
      const next = { ...prev } as any;
      if (name === 'notional') next.notional = validateNotional(String(processed));
      if (name === 'fixed_rate') next.fixed_rate = validateFixedRate(Number(processed));
      if (name === 'maturity_date') next.maturity_date = validateMaturity(String(processed), maturityInputType);
      if (name === 'direction') next.direction = null;
      return next;
    });
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
        body: JSON.stringify({
          ...formData,
          yield_curve_overrides: curveOverrides.length > 0 ? curveOverrides : undefined,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to price swap');
      }
      
      const data = await response.json();
      setResult(`Swap Value: $${data.swap_value.toFixed(2)}`);
      setPaymentSchedule(data.schedule || []);
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
          maturity_date: formData.maturity_date,
          yield_curve_overrides: curveOverrides.length > 0 ? curveOverrides : undefined,
        }),
      });
      
      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || 'Failed to solve par rate');
      }
      
      const data = await response.json();
      setFormData(prev => ({ ...prev, fixed_rate: data.par_rate }));
      setParRate(data.par_rate);
      setPaymentSchedule([]);
      setSuccess(`Par rate solved: ${data.par_rate.toFixed(4)}%`);
    } catch (err) {
      setError(`${err}`);
    } finally {
      setLoading(false);
    }
  };

  // Export & Print helpers
  const downloadJSON = () => {
    const blob = new Blob([JSON.stringify({
      inputs: formData,
      schedule: paymentSchedule,
      totals,
    }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'swap_results.json';
    a.click();
    URL.revokeObjectURL(url);
  };

  const downloadCSV = () => {
    if (!paymentSchedule || paymentSchedule.length === 0) return;
    const headers = ['payment_date','days','fixed_payment','floating_payment','discount_factor','pv_fixed','pv_floating'];
    const lines = [headers.join(',')].concat(paymentSchedule.map((row: any) => headers.map(h => row[h]).join(',')));
    const blob = new Blob([lines.join('\n')], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'swap_schedule.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  const printReport = () => {
    window.print();
  };

  // Upload custom curve CSV -> set overrides and preview
  const handleCurveCSVUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    try {
      const fd = new FormData();
      fd.append('file', file);
      const resp = await fetch(`${API_BASE_URL}/parse-curve-csv`, { method: 'POST', body: fd });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Upload failed (${resp.status})`);
      }
      const data = await resp.json();
      setCurveOverrides(data.yield_curve_overrides || []);
      if (data.yield_curve) setYieldCurve(data.yield_curve);
      if (data.plot_data) setPlotData(data.plot_data);
      setSuccess('Custom curve parsed. Overrides applied for pricing.');
    } catch (err) {
      setError(`${err}`);
    }
  };

  return (
    <div className="container">
      <h1>Interest Rate Swap Pricer</h1>
      <p>Price interest rate swaps and solve for par rates using yield curve data</p>
      
      {/* Backend Status */}
      <div className={`status-indicator ${backendConnected ? 'status-connected' : 'status-disconnected'}`}>
        <span>{backendConnected ? '🟢' : '🔴'}</span>
        <span>Backend Status: {backendConnected ? 'Connected' : 'Disconnected'}</span>
        {!backendConnected && <span className="loading-spinner"></span>}
      </div>

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

      {/* Locale & Currency Selector */}
      <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '0.5rem', gap: '1rem' }}>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Locale:
          <select value={locale} onChange={(e) => setLocale(e.target.value)} className="form-input" style={{ width: 'auto' }}>
            <option value="en-US">English (US)</option>
            <option value="en-GB">English (UK)</option>
            <option value="fr-FR">Français (FR)</option>
            <option value="de-DE">Deutsch (DE)</option>
            <option value="ja-JP">日本語 (JP)</option>
          </select>
        </label>
        <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
          Currency:
          <select value={currency} onChange={(e) => setCurrency(e.target.value)} className="form-input" style={{ width: 'auto' }}>
            <option value="USD">USD</option>
            <option value="EUR">EUR</option>
            <option value="GBP">GBP</option>
            <option value="JPY">JPY</option>
            <option value="CHF">CHF</option>
            <option value="AUD">AUD</option>
            <option value="CAD">CAD</option>
          </select>
        </label>
      </div>

      {/* Pricing Form */}
      <div className="card">
        <h2>🏦 Interest Rate Swap Parameters</h2>
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
                aria-invalid={!!errors.notional}
                className="form-input"
              />
              {errors.notional && (
                <div className="inline-error">{errors.notional}</div>
              )}
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
                min={-10}
                max={50}
                aria-invalid={!!errors.fixed_rate}
                className="form-input"
              />
              {errors.fixed_rate && (
                <div className="inline-error">{errors.fixed_rate}</div>
              )}
            </div>

            <div className="form-group" style={{ marginTop: '0.5rem' }}>
              <label className="form-label">Business Day Convention</label>
              <select value={bdc} onChange={(e) => setBdc(e.target.value)} className="form-input" style={{ width: 'auto' }}>
                <option>None</option>
                <option>Following</option>
                <option>Modified Following</option>
                <option>Preceding</option>
              </select>
              <div style={{ color: '#94a3b8', marginTop: '0.25rem' }}>Calendars are simplified (weekends only) and not applied to pricing yet; selection is for reporting/UI purposes.</div>
            </div>

            <div className="form-group">
              <label className="form-label" htmlFor="maturity_date">Maturity</label>
              <div style={{ display: 'flex', gap: '1rem', alignItems: 'center', marginBottom: '0.25rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="radio"
                    name="maturity_mode"
                    value="tenor"
                    checked={maturityInputType === 'tenor'}
                    onChange={() => setMaturityInputType('tenor')}
                  />
                  Tenor (e.g., 5y, 18m)
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                  <input
                    type="radio"
                    name="maturity_mode"
                    value="date"
                    checked={maturityInputType === 'date'}
                    onChange={() => setMaturityInputType('date')}
                  />
                  Absolute date (YYYY-MM-DD)
                </label>
              </div>
              {maturityInputType === 'date' ? (
                <>
                  <input
                    type="date"
                    id="maturity_date"
                    name="maturity_date"
                    value={/\d{4}-\d{2}-\d{2}/.test(formData.maturity_date) ? formData.maturity_date : ''}
                    onChange={handleInputChange}
                    aria-invalid={!!errors.maturity_date}
                    className="form-input"
                  />
                  {errors.maturity_date && (
                    <div className="inline-error">{errors.maturity_date}</div>
                  )}
                </>
              ) : (
                <>
                  <input
                    type="text"
                    id="maturity_date"
                    name="maturity_date"
                    value={formData.maturity_date}
                    onChange={handleInputChange}
                    placeholder="e.g., 5y or 2028-12-31"
                    pattern="^\\d+\\s*[ymdYMD]$"
                    aria-invalid={!!errors.maturity_date}
                    className="form-input"
                  />
                  {errors.maturity_date && (
                    <div className="inline-error">{errors.maturity_date}</div>
                  )}
                </>
              )}
            </div>
          </div>

          <div className="form-group" style={{ marginTop: '0.5rem' }}>
            <label className="form-label">Swap Side</label>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="radio"
                  name="direction"
                  value="payer"
                  checked={formData.direction === 'payer'}
                  onChange={handleInputChange}
                />
                Payer (pay fixed)
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                <input
                  type="radio"
                  name="direction"
                  value="receiver"
                  checked={formData.direction === 'receiver'}
                  onChange={handleInputChange}
                />
                Receiver (receive fixed)
              </label>
            </div>
            <div style={{ color: '#94a3b8', marginTop: '0.25rem' }}>
              Convention: Positive PV means value to the selected side. Receiver PV flips the sign relative to Payer.
            </div>
          </div>

          <div>
            <button
              type="button"
              onClick={handlePriceSwap}
              disabled={loading || !backendConnected || !isFormValid}
              className="btn btn-primary"
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Pricing...
                </>
              ) : (
                'Price Swap'
              )}
            </button>

            <button
              type="button"
              onClick={handleSolveParRate}
              disabled={loading || !backendConnected || !isFormValid}
              className="btn btn-secondary"
            >
              {loading ? (
                <>
                  <span className="loading-spinner"></span>
                  Solving...
                </>
              ) : (
                'Solve Par Rate'
              )}
            </button>
          </div>
        </form>
      </div>

      {/* Results */}
      {(result || parRate !== null) && (
        <div className="card">
          <h2>📊 Calculation Results</h2>
          <div className="alert alert-success">
            {parRate !== null && (
              <div><strong>Par Rate:</strong> {parRate.toFixed(4)}%</div>
            )}
            {result && (
              <div><strong>{result}</strong></div>
            )}
          </div>
          {paymentSchedule.length > 0 && (
            <div style={{ marginTop: '1rem' }}>
              <div className="summary-panel">
                <div><strong>Payments:</strong> {totals.count}</div>
                <div><strong>PV Fixed:</strong> {currencyFormatter.format(totals.pvFixed)}</div>
                <div><strong>PV Floating:</strong> {currencyFormatter.format(totals.pvFloating)}</div>
                <div><strong>NPV (Floating - Fixed):</strong> {currencyFormatter.format(totals.npv)}</div>
              </div>
              <div style={{ marginTop: '0.5rem', color: '#94a3b8' }}>
                <p>📅 <strong>Payment Frequency:</strong> Semi-annual (every 6 months)</p>
              </div>
              {/* Export & Print */}
              <div style={{ marginTop: '0.5rem', display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                <button type="button" className="btn btn-secondary" onClick={downloadJSON} disabled={paymentSchedule.length === 0}>⬇️ Download JSON</button>
                <button type="button" className="btn btn-secondary" onClick={downloadCSV} disabled={paymentSchedule.length === 0}>⬇️ Download CSV</button>
                <button type="button" className="btn btn-secondary" onClick={printReport}>🖨️ Print Report</button>
              </div>
              {/* Cashflow Visualization */}
              <div style={{ marginTop: '1rem' }}>
                <h3>Cashflows Over Time</h3>
                {paymentSchedule.length > 0 ? (
                  (() => {
                    const padding = { top: 20, right: 20, bottom: 60, left: 60 };
                    const barWidth = 14;
                    const gap = 10;
                    const groupGap = 20;
                    const n = paymentSchedule.length;
                    const width = Math.max(600, padding.left + padding.right + n * (barWidth * 2 + gap) + (n - 1) * groupGap);
                    const height = 260;
                    const pvPairs = paymentSchedule.map(p => ({ fixed: Math.abs(Number(p.pv_fixed || 0)), floating: Math.abs(Number(p.pv_floating || 0)) }));
                    const maxVal = Math.max(1, ...pvPairs.flatMap(o => [o.fixed, o.floating]));
                    const scaleY = (v: number) => (height - padding.bottom) - (v / maxVal) * (height - padding.top - padding.bottom);
                    const xStart = padding.left;

                    const dateLabels = paymentSchedule.map(p => new Date(p.payment_date));
                    const dateFmt = dateFormatter;

                    return (
                      <div role="img" aria-label="Bar chart of fixed and floating present values per payment date" style={{ overflowX: 'auto' }}>
                        <svg width={width} height={height}>
                          {/* Axes */}
                          <line x1={padding.left} y1={height - padding.bottom} x2={width - padding.right} y2={height - padding.bottom} stroke="#94a3b8" />
                          <line x1={padding.left} y1={padding.top} x2={padding.left} y2={height - padding.bottom} stroke="#94a3b8" />
                          {/* Y axis labels */}
                          {Array.from({ length: 5 }).map((_, i) => {
                            const v = (maxVal * i) / 4;
                            const y = scaleY(v);
                            return (
                              <g key={i}>
                                <line x1={padding.left - 4} y1={y} x2={width - padding.right} y2={y} stroke="#e2e8f0" strokeDasharray="4,4" />
                                <text x={padding.left - 8} y={y + 4} fontSize="10" textAnchor="end" fill="#64748b">
                                  {currencyFormatter.format(v)}
                                </text>
                              </g>
                            );
                          })}
                          {/* Bars and X labels */}
                          {paymentSchedule.map((p, idx) => {
                            const groupX = xStart + idx * (barWidth * 2 + gap + groupGap);
                            const fixedVal = pvPairs[idx].fixed;
                            const floatVal = pvPairs[idx].floating;
                            const fxY = scaleY(fixedVal);
                            const flY = scaleY(floatVal);
                            const baseY = height - padding.bottom;
                            return (
                              <g key={idx}>
                                <rect x={groupX} y={fxY} width={barWidth} height={baseY - fxY} fill="#ef4444" aria-label={`Fixed PV ${currencyFormatter.format(fixedVal)}`} />
                                <rect x={groupX + barWidth + gap} y={flY} width={barWidth} height={baseY - flY} fill="#10b981" aria-label={`Floating PV ${currencyFormatter.format(floatVal)}`} />
                                <text x={groupX + barWidth} y={baseY + 14} fontSize="10" textAnchor="middle" fill="#475569" transform={`rotate(30 ${groupX + barWidth} ${baseY + 14})`}>
                                  {dateFmt.format(dateLabels[idx])}
                                </text>
                              </g>
                            );
                          })}
                          {/* Legend */}
                          <g>
                            <rect x={padding.left} y={height - padding.bottom + 24} width={10} height={10} fill="#ef4444" />
                            <text x={padding.left + 16} y={height - padding.bottom + 33} fontSize="12" fill="#475569">Fixed PV</text>
                            <rect x={padding.left + 90} y={height - padding.bottom + 24} width={10} height={10} fill="#10b981" />
                            <text x={padding.left + 106} y={height - padding.bottom + 33} fontSize="12" fill="#475569">Floating PV</text>
                          </g>
                        </svg>
                      </div>
                    );
                  })()
                ) : (
                  <p style={{ color: '#64748b' }}>No cashflows available. Price a swap to see the visualization.</p>
                )}
              </div>
            </div>
          )}
        </div>
      )}

      {/* Data Tabs */}
      <div className="card">
        <Tabs
          tabs={[
            {
              id: 'yield-curve',
              label: '📈 Yield Curve',
              content: (
                <>
                  {plotData && (
                    <YieldCurveChart plotData={plotData} className="chart-container" />
                  )}

                  {/* Editable Overrides */}
                  <div style={{ margin: '1rem 0' }}>
                    <h3>Override Yield Curve Points (optional)</h3>
                    <p style={{ color: '#64748b' }}>Add or edit points below to override the default curve rates for matching maturities. Rates are in percent.</p>
                    {/* Upload custom curve CSV */}
                    <div style={{ margin: '0.5rem 0' }}>
                      <label className="form-label" htmlFor="curveCsv">Upload custom curve CSV</label>
                      <input id="curveCsv" type="file" accept=".csv,text/csv" onChange={handleCurveCSVUpload} className="form-input" />
                      <div style={{ color: '#94a3b8', fontSize: '0.9rem' }}>Expected columns: Maturity (Years), Rate (percent). File is parsed client-side and applied as overrides.</div>
                    </div>
                    <button
                      type="button"
                      className="btn btn-secondary"
                      onClick={() => setCurveOverrides(prev => [...prev, { maturity_years: 1, rate: 5 }])}
                      style={{ marginBottom: '0.5rem' }}
                    >
                      + Add Point
                    </button>
                    {curveOverrides.length > 0 && (
                      <table className="table">
                        <thead>
                          <tr>
                            <th>Maturity (Years)</th>
                            <th>Rate (%)</th>
                            <th></th>
                          </tr>
                        </thead>
                        <tbody>
                          {curveOverrides.map((row, idx) => (
                            <tr key={idx}>
                              <td>
                                <input
                                  type="number"
                                  min={0}
                                  step={0.25}
                                  value={row.maturity_years}
                                  onChange={(e) => {
                                    const v = parseFloat(e.target.value || '0');
                                    setCurveOverrides(prev => prev.map((r, i) => i === idx ? { ...r, maturity_years: v } : r));
                                  }}
                                  className="form-input"
                                />
                              </td>
                              <td>
                                <input
                                  type="number"
                                  step={0.01}
                                  value={row.rate}
                                  onChange={(e) => {
                                    const v = parseFloat(e.target.value || '0');
                                    setCurveOverrides(prev => prev.map((r, i) => i === idx ? { ...r, rate: v } : r));
                                  }}
                                  className="form-input"
                                />
                              </td>
                              <td>
                                <button
                                  type="button"
                                  className="btn btn-link"
                                  onClick={() => setCurveOverrides(prev => prev.filter((_, i) => i !== idx))}
                                >
                                  Remove
                                </button>
                              </td>
                            </tr>
                          ))}
                        </tbody>
                      </table>
                    )}
                  </div>

                  {/* Base curve display */}
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
                            <td>{dateFormatter.format(new Date(point.Date))}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  ) : (
                    <p>Loading yield curve data...</p>
                  )}
                </>
              )
            },
            {
              id: 'payment-schedule',
              label: '📋 Payment Schedule',
              content: paymentSchedule.length > 0 ? (
                <table className="table">
                  <thead>
                    <tr>
                      <th>Payment Date</th>
                      <th>Days</th>
                      <th className="text-right">Fixed Payment</th>
                      <th className="text-right">Floating Payment</th>
                      <th className="text-right">Discount Factor</th>
                      <th className="text-right">Fixed PV</th>
                      <th className="text-right">Floating PV</th>
                    </tr>
                  </thead>
                  <tbody>
                    {paymentSchedule.map((payment, index) => (
                      <tr key={index}>
                        <td>{dateFormatter.format(new Date(payment.payment_date))}</td>
                        <td>{payment.days}</td>
                        <td className="text-right">{currencyFormatter.format(payment.fixed_payment)}</td>
                        <td className="text-right">{currencyFormatter.format(payment.floating_payment)}</td>
                        <td className="text-right">{payment.discount_factor.toFixed(6)}</td>
                        <td className="text-right">{currencyFormatter.format(payment.pv_fixed)}</td>
                        <td className="text-right">{currencyFormatter.format(payment.pv_floating)}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              ) : (
                <p>No payment schedule available. Price a swap to see the payment schedule.</p>
              )
            }
          ]}
          defaultTab="yield-curve"
        />
      </div>
    </div>
  );
}

export default App;
