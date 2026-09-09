import type { AppointmentInput, AuthUser, BackendAppointment, Customer, Health, InteractionAction, PreferencePatch, Preferences, Property, RecommendationResponse, SearchFilters } from "@/types/api";

const API_URL = (process.env.NEXT_PUBLIC_SARA_API_URL || "http://localhost:8010").replace(/\/$/, "");
let csrfToken: string | null = null;

export class ApiError extends Error {
  constructor(message: string, public status = 0) { super(message); }
}

function validationMessage(detail: unknown): string {
  if (Array.isArray(detail) && detail.length) {
    const issue = detail[0] as { loc?: unknown[]; msg?: string };
    const field = issue.loc?.at(-1);
    return `${field ? `${String(field).replaceAll("_", " ")}: ` : ""}${issue.msg || "Invalid value"}`;
  }
  return typeof detail === "string" ? detail : "The request could not be completed.";
}

function combineHeaders(initHeaders?: HeadersInit, csrf?: string | null): Record<string, string> {
  const result: Record<string, string> = {
    "Content-Type": "application/json",
  };

  if (initHeaders) {
    if (initHeaders instanceof Headers) {
      initHeaders.forEach((value, key) => {
        result[key] = value;
      });
    } else if (Array.isArray(initHeaders)) {
      for (const [key, value] of initHeaders) {
        result[key] = value;
      }
    } else if (typeof initHeaders === "object") {
      for (const [key, value] of Object.entries(initHeaders)) {
        if (value !== undefined) {
          result[key] = String(value);
        }
      }
    }
  }

  for (const key of Object.keys(result)) {
    if (key.toLowerCase() === "x-csrf-token") {
      delete result[key];
    }
  }

  if (csrf) {
    result["X-CSRF-Token"] = csrf;
  }

  return result;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    const headers = combineHeaders(init?.headers, csrfToken);
    response = await fetch(`${API_URL}${path}`, { ...init, credentials: "include", headers });

    if (response.status === 403 && !["GET", "HEAD", "OPTIONS"].includes((init?.method || "GET").toUpperCase())) {
      const rejected = await response.clone().json().catch(() => ({}));
      if (rejected.detail === "CSRF validation failed") {
        const csrfRes = await fetch(`${API_URL}/api/auth/csrf`, { credentials: "include" });
        if (csrfRes.ok) {
          const data = await csrfRes.json().catch(() => ({}));
          const token = typeof data.csrf_token === "string" && data.csrf_token ? data.csrf_token : (typeof data.csrfToken === "string" ? data.csrfToken : null);
          if (token) {
            csrfToken = token;
            const retryHeaders = combineHeaders(init?.headers, csrfToken);
            response = await fetch(`${API_URL}${path}`, { ...init, credentials: "include", headers: retryHeaders });
          }
        }
      }
    }
  } catch {
    throw new ApiError("Could not reach Sara backend. Please check that it is running.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401) {
      throw new ApiError(typeof body.detail === "string" && body.detail ? body.detail : "Authentication required. Please sign in to continue.", 401);
    }
    if (response.status === 403) {
      throw new ApiError(typeof body.detail === "string" && body.detail ? body.detail : "Security request validation failed.", 403);
    }
    throw new ApiError(validationMessage(body.detail), response.status);
  }
  return body as T;
}

export const api = {
  startVoice: () => request<{ voice_session: string; assistant_id: string; preferences?: PreferencePatch }>("/api/me/voice-sessions", { method: "POST", body: "{}" }),
  closeVoice: (voiceSession: string) => request<void>("/api/me/voice-sessions/close", { method: "POST", body: JSON.stringify({ voice_session: voiceSession }) }),
  chat: (message: string, conversationId?: string) => request<import("@/types/api").ChatResponse>("/api/me/chat", { method: "POST", body: JSON.stringify({ message, ...(conversationId ? { conversation_id: conversationId } : {}) }) }),
  register: (body: { full_name: string; email: string; phone: string; password: string }) => request<AuthUser>("/api/auth/register", { method: "POST", body: JSON.stringify(body) }),
  login: (body: { email: string; password: string }) => request<AuthUser>("/api/auth/login", { method: "POST", body: JSON.stringify(body) }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  logoutAll: () => request<void>("/api/auth/logout-all", { method: "POST" }),
  me: () => request<AuthUser>("/api/auth/me"),
  getHealth: () => request<Health>("/health"),
  createCustomer: (body: { full_name: string; email?: string; phone: string }) => request<Customer>("/api/customers", { method: "POST", body: JSON.stringify(body) }),
  getCustomer: (id: string) => request<Customer>(`/api/customers/${id}`),
  getPreferences: (id: string) => request<Preferences>(`/api/customers/${id}/preferences`),
  updatePreferences: (id: string, body: PreferencePatch) => request<Preferences>(`/api/customers/${id}/preferences`, { method: "PATCH", body: JSON.stringify(body) }),
  searchProperties: (body: SearchFilters) => request<Property[]>("/api/properties/search", { method: "POST", body: JSON.stringify(body) }),
  getRecommendations: (customerId: string, sessionId: string, limit = 10) => request<RecommendationResponse>(`/api/customers/${customerId}/recommendations`, { method: "POST", body: JSON.stringify({ recommendation_session_id: sessionId, limit }) }),
  recordInteraction: (customerId: string, propertyId: string, action: InteractionAction, sessionId: string) => request<{ interaction_id: string }>("/api/interactions", { method: "POST", body: JSON.stringify({ customer_id: customerId, property_id: propertyId, action, recommendation_session_id: sessionId }) }),
  bookAppointment: (body: AppointmentInput) => request<Record<string, unknown>>("/api/appointments", { method: "POST", body: JSON.stringify(body) }),
  rescheduleAppointment: (id: string, startsAt: string) => request<Record<string, unknown>>(`/api/appointments/${id}/reschedule`, { method: "PATCH", body: JSON.stringify({ starts_at: startsAt }) }),
  cancelAppointment: (id: string) => request<Record<string, unknown>>(`/api/appointments/${id}`, { method: "DELETE" }),
  getMyPreferences: () => request<Preferences>("/api/me/preferences"),
  updateMyPreferences: (body: PreferencePatch) => request<Preferences>("/api/me/preferences", { method: "PATCH", body: JSON.stringify(body) }),
  searchMyProperties: (body: Omit<SearchFilters, "customer_id">) => request<Property[]>("/api/me/properties/search", { method: "POST", body: JSON.stringify(body) }),
  getMyRecommendations: (sessionId: string, limit = 10) => request<RecommendationResponse>("/api/me/recommendations", { method: "POST", body: JSON.stringify({ recommendation_session_id: sessionId, limit }) }),
  recordMyInteraction: (propertyId: string, action: InteractionAction, sessionId: string) => request<{ interaction_id: string }>("/api/me/interactions", { method: "POST", body: JSON.stringify({ property_id: propertyId, action, recommendation_session_id: sessionId }) }),
  bookMyAppointment: (body: Omit<AppointmentInput, "customer_id">) => request<Record<string, unknown>>("/api/me/appointments", { method: "POST", body: JSON.stringify(body) }),
  getMyAppointments: () => request<{ appointments: BackendAppointment[] }>("/api/me/appointments"),
};
