/**
 * mlApi.ts
 * --------
 * TypeScript client for Week 8 Machine Learning & Serving Platform.
 * Consumes Week 8 FastAPI endpoints:
 * - POST /predict/price       : Point valuation, quantile bounds (P10, P50, P90), and verdict
 * - POST /predict/lead-score  : Lead conversion probability, tier, persona, and SLA action
 * - POST /explain/lead        : TreeSHAP local feature attribution and UrduLish rationale
 * - POST /explain/price       : Feature attribution status contract
 * - GET  /market/stats        : Exact aggregations from data/processed/properties_clean.csv
 * - GET  /market/insights     : City-wide market distributions and comparisons
 * - POST /assistant/chat      : LangGraph AI Assistant with 5 tools & numeric fact guard
 * - GET  /health              : Model artifact liveness verification
 * - GET  /model/info          : Provenance, versions, and verified metrics
 */

const ML_API_URL = (
  process.env.NEXT_PUBLIC_WEEK8_API_URL ||
  (process.env.NODE_ENV !== "production" ? "http://localhost:8000" : "")
).replace(/\/$/, "");

export class MlApiError extends Error {
  constructor(message: string, public status = 0, public detail?: unknown) {
    super(message);
    this.name = "MlApiError";
  }
}

// ==============================================================================
// 1. Price Valuation Types
// ==============================================================================

export interface PricePredictionRequest {
  purpose: "For Sale" | "For Rent" | string;
  property_type: string;
  city: "Lahore" | "Karachi" | "Islamabad" | "Rawalpindi" | "Faisalabad" | string;
  location: string;
  area_marla: number;
  bedrooms?: number;
  baths?: number;
  price?: number; // Optional listed price to evaluate verdict
  floors?: number;
}

export interface PricePredictionResponse {
  purpose: string;
  predicted_fair_price_pkr: number;
  lower_bound_pkr: number;
  upper_bound_pkr: number;
  confidence_band_pkr: [number, number];
  listed_price_pkr: number | null;
  verdict: "Fair Market Value" | "Overpriced" | "Underpriced" | string;
  deviation_percentage: number;
  human_readable_summary: string;
  inference_latency_ms: number;
  model_version: string;
  disclaimer?: string;
}

// ==============================================================================
// 2. Lead Scoring Types
// ==============================================================================

export interface LeadScoringRequest {
  lead_source: string;
  preferred_city: string;
  preferred_location: string;
  property_type: string;
  purpose: string;
  budget_pkr: number;
  number_of_calls?: number;
  total_call_duration_min?: number;
  response_time_minutes?: number;
  visit_booked?: number;
  days_since_first_contact?: number;
  follow_up_count?: number;
  budget_match_ratio?: number;
  objection_raised?: string;
}

export interface LeadScoringResponse {
  conversion_probability: number;
  lead_score_pct: number;
  training_label_provenance: "synthetic" | string;
  crm_validated: boolean;
  tier: "Hot" | "Warm" | "Cold" | string;
  priority_rank: number;
  recommended_sla_action: string;
  customer_persona: string;
  persona_cluster_id: number;
  urdulish_explanation: string;
  inference_latency_ms: number;
  model_version: string;
}

// ==============================================================================
// 3. Explainability Types
// ==============================================================================

export interface FeatureShapContribution {
  feature: string;
  shap_value: number;
}

export interface LeadExplanationResponse {
  conversion_probability: number;
  tier: string;
  top_positive_features: FeatureShapContribution[];
  top_negative_features: FeatureShapContribution[];
  urdulish_explanation: string;
  inference_latency_ms: number;
}

export interface PriceExplanationResponse {
  status: string;
  message: string;
  explanation_available: boolean;
  predicted_fair_price_pkr: number | null;
  lower_bound_pkr: number | null;
  upper_bound_pkr: number | null;
  top_features: Array<FeatureShapContribution & { direction: "increases" | "decreases" }>;
  urdulish_summary: string | null;
  inference_latency_ms: number;
  model_version: string;
  target_scale: "log_price" | string;
}

// ==============================================================================
// 4. Market Insights Types
// ==============================================================================

export interface MarketStatItem {
  available: boolean;
  found: boolean;
  record_count: number;
  total_listings_matched: number;
  city: string;
  location: string;
  purpose: string;
  avg_price_per_marla_pkr: number;
  average_price_per_marla_pkr: number;
  median_price_per_marla_pkr: number;
  min_price_per_marla_pkr: number;
  max_price_per_marla_pkr: number;
}

export interface MarketInsightsResponse {
  total_dataset_records: number;
  cities: string[];
  sale_by_city: MarketStatItem[];
  rent_by_city: MarketStatItem[];
}

export interface Week8Property {
  property_id: string;
  raw_property_id?: string;
  property_name: string;
  property_type: string;
  city: string;
  location: string;
  province_name: string;
  area: string;
  area_marla: number;
  bedrooms?: number | null;
  bathrooms?: number | null;
  baths?: number | null;
  price: number;
  price_pkr: number;
  purpose: string;
  latitude?: number | null;
  longitude?: number | null;
  agency?: string;
  agent?: string;
  page_url?: string;
  available: boolean;
  status: string;
}

export interface Week8PropertiesResponse {
  total: number;
  properties: Week8Property[];
}

export interface Week8Lead {
  id: string;
  lead_id: string;
  name: string;
  phone: string;
  city: string;
  location: string;
  preferred_city: string;
  preferred_location: string;
  budget_pkr: number;
  property_type: string;
  purpose: string;
  lead_source: string;
  calls: number;
  number_of_calls: number;
  duration_min: number;
  total_call_duration_min: number;
  response_time_minutes: number;
  visit_booked: number;
  days_since_first_contact: number;
  objection_raised: string;
  follow_up_count: number;
  budget_match_ratio: number;
  converted: number;
  tier: "Hot" | "Warm" | "Cold" | string;
  lead_score_pct: number;
}

export interface Week8LeadsResponse {
  total: number;
  leads: Week8Lead[];
}

// ==============================================================================
// 5. AI Assistant Types
// ==============================================================================

export interface ChatRequest {
  message: string;
  conversation_id?: string;
}

export interface ChatResponse {
  response: string;
  intent: string;
  tool_calls: string[];
  tool_results: Record<string, any>;
  missing_fields: string[];
  language: string;
  guard_triggered: boolean;
  inference_latency_ms: number;
}

// ==============================================================================
// Request Helper
// ==============================================================================

async function fetchWithFallback(url: string, init?: RequestInit): Promise<Response> {
  try {
    return await fetch(url, init);
  } catch (err) {
    if (url.includes("localhost")) {
      const fallbackUrl = url.replace("localhost", "127.0.0.1");
      return await fetch(fallbackUrl, init);
    }
    if (url.includes("127.0.0.1")) {
      const fallbackUrl = url.replace("127.0.0.1", "localhost");
      return await fetch(fallbackUrl, init);
    }
    throw err;
  }
}

async function mlRequest<T>(path: string, options?: RequestInit): Promise<T> {
  if (!ML_API_URL) {
    throw new MlApiError(
      "Week 8 ML API is not configured. Set NEXT_PUBLIC_WEEK8_API_URL to the deployed FastAPI service URL.",
      0
    );
  }

  const url = `${ML_API_URL}${path}`;
  try {
    const res = await fetchWithFallback(url, {
      ...options,
      headers: {
        "Content-Type": "application/json",
        ...(options?.headers || {}),
      },
    });

    if (!res.ok) {
      const errorJson = await res.json().catch(() => ({}));
      const msg =
        typeof errorJson.detail === "string"
          ? errorJson.detail
          : errorJson.errors
          ? JSON.stringify(errorJson.errors)
          : `ML API HTTP Error ${res.status}`;
      throw new MlApiError(msg, res.status, errorJson);
    }

    return (await res.json()) as T;
  } catch (err: any) {
    if (err instanceof MlApiError) {
      throw err;
    }
    throw new MlApiError(
      `Could not connect to Week 8 ML Serving Service at ${ML_API_URL}. Verify the Railway service is running and allows requests from this website.`,
      0,
      err
    );
  }
}

// ==============================================================================
// Exported mlApi Client
// ==============================================================================

export const mlApi = {
  getHealth: () =>
    mlRequest<{ status: string; models_loaded: Record<string, boolean>; system_ready: boolean }>(
      "/health"
    ),

  getModelInfo: () =>
    mlRequest<{ service: string; models: Record<string, any> }>("/model/info"),

  predictPrice: (payload: PricePredictionRequest) =>
    mlRequest<PricePredictionResponse>("/predict/price", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  scoreLead: (payload: LeadScoringRequest) =>
    mlRequest<LeadScoringResponse>("/predict/lead-score", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  explainLead: (payload: LeadScoringRequest) =>
    mlRequest<LeadExplanationResponse>("/explain/lead", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  explainPrice: (payload: PricePredictionRequest) =>
    mlRequest<PriceExplanationResponse>("/explain/price", {
      method: "POST",
      body: JSON.stringify(payload),
    }),

  getMarketStats: (city?: string, location?: string, purpose = "For Sale") => {
    const params = new URLSearchParams();
    if (city) params.set("city", city);
    if (location) params.set("location", location);
    if (purpose) params.set("purpose", purpose);
    return mlRequest<MarketStatItem>(`/market/stats?${params.toString()}`);
  },

  getMarketInsights: () =>
    mlRequest<MarketInsightsResponse>("/market/insights"),

  chatAssistant: (message: string, conversationId?: string) =>
    mlRequest<ChatResponse>("/assistant/chat", {
      method: "POST",
      body: JSON.stringify({ message, conversation_id: conversationId }),
    }),

  getRealLeads: async () => {
    const saraUrl = (process.env.NEXT_PUBLIC_SARA_API_URL || "http://localhost:8010").replace(/\/$/, "");
    try {
      const res = await fetch(`${saraUrl}/api/agent/leads`, { credentials: "include" });
      if (res.ok) {
        return (await res.json()) as Array<{
          id: string;
          name: string;
          phone: string;
          city: string;
          location: string;
          budget_pkr: number;
          lead_source: string;
          calls: number;
          duration_min: number;
          visit_booked: number;
        }>;
      }
    } catch {
      // fallback handled in UI
    }
    return [];
  },

  getProperties: (filters?: {
    city?: string;
    location?: string;
    property_type?: string;
    purpose?: string;
    min_price?: number;
    max_price?: number;
    bedrooms?: number;
    limit?: number;
    offset?: number;
  }) => {
    const params = new URLSearchParams();
    if (filters?.city) params.set("city", filters.city);
    if (filters?.location) params.set("location", filters.location);
    if (filters?.property_type) params.set("property_type", filters.property_type);
    if (filters?.purpose) params.set("purpose", filters.purpose);
    if (filters?.min_price) params.set("min_price", String(filters.min_price));
    if (filters?.max_price) params.set("max_price", String(filters.max_price));
    if (filters?.bedrooms) params.set("bedrooms", String(filters.bedrooms));
    if (filters?.limit) params.set("limit", String(filters.limit));
    if (filters?.offset) params.set("offset", String(filters.offset));
    return mlRequest<Week8PropertiesResponse>(`/properties?${params.toString()}`);
  },

  getProperty: (propertyId: string | number) =>
    mlRequest<Week8Property>(`/properties/${propertyId}`),

  getLeads: (filters?: {
    limit?: number;
    offset?: number;
    tier?: string;
    city?: string;
    source?: string;
    search?: string;
  }) => {
    const params = new URLSearchParams();
    if (filters?.limit) params.set("limit", String(filters.limit));
    if (filters?.offset) params.set("offset", String(filters.offset));
    if (filters?.tier) params.set("tier", filters.tier);
    if (filters?.city) params.set("city", filters.city);
    if (filters?.source) params.set("source", filters.source);
    if (filters?.search) params.set("search", filters.search);
    return mlRequest<Week8LeadsResponse>(`/leads?${params.toString()}`);
  },

  getLead: (leadId: string) =>
    mlRequest<Week8Lead>(`/leads/${leadId}`),
};
