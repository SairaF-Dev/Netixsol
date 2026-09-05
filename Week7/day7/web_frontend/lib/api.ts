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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_URL}${path}`, { ...init, credentials: "include", headers: { "Content-Type": "application/json", ...(csrfToken ? { "X-CSRF-Token": csrfToken } : {}), ...init?.headers } });
    if (response.status === 403 && !csrfToken && !["GET", "HEAD", "OPTIONS"].includes((init?.method || "GET").toUpperCase())) {
      const rejected = await response.clone().json().catch(() => ({}));
      if (rejected.detail === "CSRF validation failed") {
        const csrf = await fetch(`${API_URL}/api/auth/csrf`, { credentials: "include" });
        if (csrf.ok) csrfToken = String((await csrf.json()).csrf_token || "") || null;
        if (csrfToken) response = await fetch(`${API_URL}${path}`, { ...init, credentials: "include", headers: { "Content-Type": "application/json", "X-CSRF-Token": csrfToken, ...init?.headers } });
      }
    }
  } catch {
    throw new ApiError("Could not reach Sara backend. Please check that it is running.");
  }
  const body = await response.json().catch(() => ({}));
  if (!response.ok) throw new ApiError(validationMessage(body.detail), response.status);
  return body as T;
}

export const api = {
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
