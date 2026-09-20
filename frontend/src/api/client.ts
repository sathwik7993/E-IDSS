// API client for the E-IDSS backend. Falls back to mock data whenever the
// backend is unreachable (e.g. during frontend-only development) so every
// view still renders. Each call reports whether it used live or mock data.

import type {
  HealthResponse,
  InspectResponse,
  MetricsResponse,
  RootCauseResponse,
  RootCauseValidationResponse,
  LineStateResponse,
  EconomicsResponse,
  CounterfactualRequest,
  CounterfactualResponse,
  LineRecommendationResponse,
  EconomicsRecommendationResponse,
  TelemetrySpecsResponse,
  AttributionResponse,
  LineHealthResponse,
  FinancialImpactResponse,
  Telemetry,
} from "../types/api";
import {
  mockTelemetrySpecs,
  mockAttribution,
  mockLineHealth,
  mockFinancialImpact,
} from "./mockTelemetry";
import {
  mockHealth,
  mockInspect,
  mockMetrics,
  mockRootCause,
  mockRootCauseValidation,
  mockLineState,
  mockEconomics,
  mockCounterfactual,
  mockLineRecommendation,
  mockEconomicsRecommendation,
} from "./mock";

export const API_BASE_URL =
  (import.meta.env.VITE_API_BASE_URL as string | undefined) ||
  "http://localhost:8000";

export class ApiResult<T> {
  data: T;
  isMock: boolean;
  constructor(data: T, isMock: boolean) {
    this.data = data;
    this.isMock = isMock;
  }
}

const REQUEST_TIMEOUT_MS = 6000;

async function fetchWithTimeout(
  input: string,
  init?: RequestInit
): Promise<Response> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    const res = await fetch(input, { ...init, signal: controller.signal });
    return res;
  } finally {
    clearTimeout(timer);
  }
}

async function safeCall<T>(
  path: string,
  init: RequestInit | undefined,
  fallback: () => T
): Promise<ApiResult<T>> {
  try {
    const res = await fetchWithTimeout(`${API_BASE_URL}${path}`, init);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = (await res.json()) as T;
    return new ApiResult(data, false);
  } catch {
    return new ApiResult(fallback(), true);
  }
}

export async function getHealth(): Promise<ApiResult<HealthResponse>> {
  return safeCall("/api/health", undefined, () => mockHealth);
}

export async function postInspect(
  file: File,
  activationThreshold = 0.5
): Promise<ApiResult<InspectResponse>> {
  const form = new FormData();
  form.append("file", file);
  return safeCall(
    `/api/inspect?activation_threshold=${activationThreshold}`,
    { method: "POST", body: form },
    () => mockInspect()
  );
}

export async function getMetrics(): Promise<ApiResult<MetricsResponse>> {
  return safeCall("/api/metrics", undefined, () => mockMetrics);
}

export async function postRootCause(
  defect_class: string
): Promise<ApiResult<RootCauseResponse>> {
  return safeCall(
    "/api/rootcause",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ defect_class, observation: null }),
    },
    () => mockRootCause(defect_class)
  );
}

export async function getRootCauseValidation(): Promise<
  ApiResult<RootCauseValidationResponse>
> {
  return safeCall(
    "/api/rootcause/validation",
    undefined,
    () => mockRootCauseValidation
  );
}

export async function getLineState(): Promise<ApiResult<LineStateResponse>> {
  return safeCall("/api/line/state", undefined, () => mockLineState);
}

export async function getEconomics(
  defect_rate: number,
  throughput: number
): Promise<ApiResult<EconomicsResponse>> {
  return safeCall(
    `/api/economics?defect_rate=${defect_rate}&throughput=${throughput}`,
    undefined,
    () => mockEconomics(defect_rate, throughput)
  );
}

export async function postCounterfactual(
  req: CounterfactualRequest
): Promise<ApiResult<CounterfactualResponse>> {
  return safeCall(
    "/api/economics/counterfactual",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(req),
    },
    () => mockCounterfactual(req)
  );
}

export async function getLineRecommendation(
  defect_rate = 0.08
): Promise<ApiResult<LineRecommendationResponse>> {
  return safeCall(
    `/api/line/recommendation?defect_rate=${defect_rate}`,
    undefined,
    () => mockLineRecommendation()
  );
}

export async function getTelemetrySpecs(): Promise<
  ApiResult<TelemetrySpecsResponse>
> {
  return safeCall("/api/telemetry/specs", undefined, () => mockTelemetrySpecs);
}

export async function postTelemetryAttribution(
  telemetry: Telemetry
): Promise<ApiResult<AttributionResponse>> {
  return safeCall(
    "/api/telemetry/attribution",
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ telemetry }),
    },
    () => mockAttribution(telemetry)
  );
}

export async function getLineHealth(): Promise<ApiResult<LineHealthResponse>> {
  return safeCall("/api/line/health", undefined, () => mockLineHealth);
}

export async function getFinancialImpact(
  daily_units: number,
  defect_rate_pct: number,
  scrap_cost_per_unit: number
): Promise<ApiResult<FinancialImpactResponse>> {
  return safeCall(
    `/api/line/financial?daily_units=${daily_units}&defect_rate_pct=${defect_rate_pct}&scrap_cost_per_unit=${scrap_cost_per_unit}`,
    undefined,
    () => mockFinancialImpact(daily_units, defect_rate_pct, scrap_cost_per_unit)
  );
}

export async function getEconomicsRecommendation(
  defect_rate: number,
  throughput: number
): Promise<ApiResult<EconomicsRecommendationResponse>> {
  return safeCall(
    `/api/economics/recommendation?defect_rate=${defect_rate}&throughput=${throughput}`,
    undefined,
    () => mockEconomicsRecommendation(defect_rate, throughput)
  );
}
