import axios from 'axios';
import {
  SwapPriceRequest,
  SwapPriceResponse,
  SolveParRateRequest,
  ParRateResponse,
  YieldCurveResponse,
  ApiError,
} from '../types/api';

// Configure axios with base URL and common settings
const api = axios.create({
  baseURL: 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.data?.detail) {
      // Return the API error detail
      return Promise.reject(new Error(error.response.data.detail));
    }
    return Promise.reject(error);
  }
);

export class IRDPricerAPI {
  /**
   * Get yield curve data and plot
   */
  static async getYieldCurve(): Promise<YieldCurveResponse> {
    try {
      const response = await api.get<YieldCurveResponse>('/yield-curve');
      return response.data;
    } catch (error) {
      throw new Error(`Failed to fetch yield curve: ${error}`);
    }
  }

  /**
   * Price an interest rate swap
   */
  static async priceSwap(request: SwapPriceRequest): Promise<SwapPriceResponse> {
    try {
      const response = await api.post<SwapPriceResponse>('/price-swap', request);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to price swap: ${error}`);
    }
  }

  /**
   * Solve for the par rate of an interest rate swap
   */
  static async solveParRate(request: SolveParRateRequest): Promise<ParRateResponse> {
    try {
      const response = await api.post<ParRateResponse>('/solve-par-rate', request);
      return response.data;
    } catch (error) {
      throw new Error(`Failed to solve par rate: ${error}`);
    }
  }

  /**
   * Health check
   */
  static async healthCheck(): Promise<{ status: string; service: string }> {
    try {
      const response = await api.get('/health');
      return response.data;
    } catch (error) {
      throw new Error(`Health check failed: ${error}`);
    }
  }
}

export default IRDPricerAPI;
