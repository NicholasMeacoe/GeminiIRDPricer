export interface YieldCurvePoint {
  maturity_years: number;
  rate: number;
}

export interface SwapPriceRequest {
  notional: string;
  fixed_rate: number;
  maturity_date: string;
  yield_curve_overrides?: YieldCurvePoint[];
}

export interface SolveParRateRequest {
  notional: string;
  maturity_date: string;
  yield_curve_overrides?: YieldCurvePoint[];
}

export interface PaymentScheduleItem {
  payment_date: string;
  days: number;
  fixed_payment: number;
  floating_payment: number;
  discount_factor: number;
  pv_fixed: number;
  pv_floating: number;
}

export interface SwapPriceResponse {
  swap_value: number;
  fixed_rate: number;
  notional: number;
  maturity_date: string;
  schedule: PaymentScheduleItem[];
}

export interface ParRateResponse {
  par_rate: number;
  notional: number;
  maturity_date: string;
}

export interface YieldCurveData {
  "Maturity (Years)": number;
  Rate: number;
  Date: string;
}

export interface YieldCurveResponse {
  yield_curve: YieldCurveData[];
  plot_data: any;
}

export interface ApiError {
  detail: string;
}
