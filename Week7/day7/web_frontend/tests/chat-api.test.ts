import { expect, it, vi } from "vitest";
it("chat reuses credentialed CSRF token retry without identity fields", async () => {
  vi.resetModules(); const { api } = await import("@/lib/api");
  const fetchMock = vi.spyOn(globalThis,"fetch").mockResolvedValueOnce(new Response(JSON.stringify({detail:"CSRF validation failed"}),{status:403})).mockResolvedValueOnce(new Response(JSON.stringify({csrf_token:"csrf"}))).mockResolvedValueOnce(new Response(JSON.stringify({conversation_id:"chat1",message:"Ji"})));
  await api.chat("Options", "chat1");
  expect(fetchMock.mock.calls[0][0]).toContain("/api/me/chat");
  expect(JSON.parse(String(fetchMock.mock.calls[0][1]?.body))).toEqual({message:"Options",conversation_id:"chat1"});
  expect(fetchMock.mock.calls[2][1]).toMatchObject({credentials:"include",headers:{"X-CSRF-Token":"csrf"}}); vi.restoreAllMocks();
});
