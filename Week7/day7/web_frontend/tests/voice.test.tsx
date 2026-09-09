import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import { SaraVoice } from "@/components/SaraVoice";
import { api } from "@/lib/api";

const sdk = vi.hoisted(() => ({ handlers: {} as Record<string, (...args: any[]) => void>,
  start: vi.fn(), stop: vi.fn(), mute: vi.fn(), remove: vi.fn(), construct: vi.fn(), send: vi.fn() }));
vi.mock("@vapi-ai/web", () => ({ default: class {
  constructor(key: string) { sdk.construct(key); }
  on(name: string, fn: (...args: any[]) => void) { sdk.handlers[name] = fn; }
  start = sdk.start; stop = sdk.stop; setMuted = sdk.mute; removeAllListeners = sdk.remove;
  send = sdk.send;
} }));
vi.mock("@/lib/api", () => ({ api: { startVoice: vi.fn(), closeVoice: vi.fn() } }));
beforeEach(() => {
  vi.clearAllMocks(); sdk.handlers = {};
  vi.stubEnv("NEXT_PUBLIC_VAPI_PUBLIC_KEY", "test-public-key");
  vi.mocked(api.startVoice).mockResolvedValue({ voice_session: "opaque-capability", assistant_id: "existing-assistant" });
  vi.mocked(api.closeVoice).mockResolvedValue(); sdk.start.mockResolvedValue({ id: "call" });
});
afterEach(() => { cleanup(); vi.unstubAllEnvs(); });
async function start() {
  fireEvent.click(screen.getByText("Start voice call"));
  await waitFor(() => expect(sdk.start).toHaveBeenCalled());
}
it("starts the existing assistant with only an opaque session identity", async () => {
  render(<SaraVoice />); await start();
  expect(sdk.construct).toHaveBeenCalledWith("test-public-key");
  expect(sdk.start).toHaveBeenCalledWith("existing-assistant", expect.objectContaining({ variableValues: { sara_voice_session: "opaque-capability" } }));
  act(() => sdk.handlers["call-start"]());
  fireEvent.click(screen.getByText("Mute microphone")); expect(sdk.mute).toHaveBeenCalledWith(true);
  fireEvent.click(screen.getByText("End call")); expect(sdk.stop).toHaveBeenCalled();
  expect(api.closeVoice).toHaveBeenCalledWith("opaque-capability");
});
it("stops and revokes on unmount or account replacement", async () => {
  const view = render(<SaraVoice />); await start(); view.unmount();
  expect(sdk.stop).toHaveBeenCalled(); expect(sdk.remove).toHaveBeenCalled();
  expect(api.closeVoice).toHaveBeenCalledWith("opaque-capability");
});
it("passes saved preferences and editing guidance to the voice assistant", async () => {
  vi.mocked(api.startVoice).mockResolvedValue({ voice_session: "opaque-capability", assistant_id: "existing-assistant",
    preferences: { city: "Karachi", budget_max: 190000000 } });
  render(<SaraVoice />); await start();
  act(() => sdk.handlers["call-start"]());
  expect(sdk.send).toHaveBeenCalledWith(expect.objectContaining({ triggerResponseEnabled: false,
    message: { role: "system", content: expect.stringContaining("editing_preferences") } }));
  expect(sdk.send.mock.calls[0][0].message.content).toContain('"city":"Karachi"');
});
it("cancels a pending bootstrap without starting a microphone session", async () => {
  let finish!: (value: any) => void;
  vi.mocked(api.startVoice).mockReturnValue(new Promise(resolve => { finish = resolve; }));
  render(<SaraVoice />); fireEvent.click(screen.getByText("Start voice call"));
  fireEvent.click(screen.getByText("Cancel call"));
  await act(async () => finish({ voice_session: "late-token", assistant_id: "existing" }));
  expect(sdk.start).not.toHaveBeenCalled(); expect(api.closeVoice).toHaveBeenCalledWith("late-token");
});
it("shows safe provider errors and allows retry", async () => {
  render(<SaraVoice />); await start();
  act(() => sdk.handlers.error({ message: "provider secret" }));
  expect(screen.getByRole("alert")).not.toHaveTextContent("provider secret");
  expect(screen.getByText("Start voice call")).toBeEnabled();
});
it("disables voice when the public key is absent", () => {
  vi.stubEnv("NEXT_PUBLIC_VAPI_PUBLIC_KEY", ""); render(<SaraVoice />);
  expect(screen.getByText("Start voice call")).toBeDisabled();
});
