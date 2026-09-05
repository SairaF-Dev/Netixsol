import { beforeEach, describe, expect, it, vi } from "vitest";
import { api, ApiError } from "@/lib/api";

const ok = (body: unknown, status = 200) => Promise.resolve(new Response(JSON.stringify(body), { status, headers: { "Content-Type": "application/json" } }));

describe("shared API client", () => {
  beforeEach(() => vi.restoreAllMocks());

  it("creates/reuses a customer through the backend", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({ customer_id: "c1", full_name: "Ali" }, 201));
    await api.createCustomer({ full_name: "Ali", email: "ali@example.com", phone: "0300" });
    expect(fetchMock).toHaveBeenCalledOnce();
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ full_name: "Ali", email: "ali@example.com", phone: "0300" });
  });

  it("loads and partially saves preferences", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({ customer_id: "c1", city: "Lahore", amenities: [] }));
    await api.getPreferences("c1");
    await api.updatePreferences("c1", { area: "DHA" });
    expect(fetchMock.mock.calls[1][0]).toContain("/api/customers/c1/preferences");
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({ area: "DHA" });
  });

  it("searches only through the property API", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok([]));
    await api.searchProperties({ city: "Lahore", limit: 20 });
    expect(fetchMock.mock.calls[0][0]).toContain("/api/properties/search");
  });

  it("preserves recommendation session IDs", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({ recommendation_session_id: "r1", ml_mode: "off", properties: [] }));
    await api.getRecommendations("c1", "r1", 10);
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({ recommendation_session_id: "r1", limit: 10 });
  });

  it.each(["liked", "rejected", "shortlisted"] as const)("records allowed %s feedback", async action => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({ interaction_id: "i1" }, 201));
    await api.recordInteraction("c1", "p1", action, "r1");
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).action).toBe(action);
  });

  it("sends timezone-aware appointment values unchanged", async () => {
    const fetchMock = vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({}, 201));
    await api.bookAppointment({ customer_id: "c1", property_id: "p1", starts_at: "2030-01-01T05:00:00.000Z", duration_minutes: 60, meeting_notes: "" });
    expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body)).starts_at).toContain("Z");
  });

  it("turns FastAPI validation into a concise field error", async () => {
    vi.spyOn(globalThis, "fetch").mockImplementation(() => ok({ detail: [{ loc: ["body", "phone"], msg: "invalid format" }] }, 422));
    await expect(api.createCustomer({ full_name: "Ali", phone: "bad" })).rejects.toMatchObject({ message: "phone: invalid format", status: 422 });
  });

  it("returns a safe network message", async () => {
    vi.spyOn(globalThis, "fetch").mockRejectedValue(new Error("socket secret detail"));
    await expect(api.getHealth()).rejects.toEqual(new ApiError("Could not reach Sara backend. Please check that it is running."));
  });
});
