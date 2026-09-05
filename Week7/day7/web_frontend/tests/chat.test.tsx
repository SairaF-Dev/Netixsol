import { fireEvent, render, screen, waitFor, cleanup } from "@testing-library/react";
import { afterEach, beforeEach, expect, it, vi } from "vitest";
import Sara from "@/app/sara/page";
import { api, ApiError } from "@/lib/api";
const mocks = vi.hoisted(() => ({ router: { replace: vi.fn() }, session: { ready: true, customer: { customer_id: "c1", full_name: "Ali" } as {customer_id:string;full_name:string} | null } }));
vi.mock("next/navigation", () => ({ useRouter: () => mocks.router }));
vi.mock("@/components/SessionProvider", () => ({ useSession: () => mocks.session }));
vi.mock("@/lib/api", async original => {
  const actual = await original<typeof import("@/lib/api")>();
  return { ...actual, api: { ...actual.api, chat: vi.fn(), recordMyInteraction: vi.fn() } };
});
const response = { conversation_id: "chat1", message: "Verified options", requires_clarification: false, recommendation_session_id: "rec1", properties: [{ property_id: "p1", property_name: "Verified home", city: "Lahore", area: "DHA", price: 30000000, currency: "PKR", bedrooms: 3, bathrooms: 2, property_type: "Apartment", purpose: "purchase", amenities: [], available: true, status: "Ready" }] };
beforeEach(() => { vi.clearAllMocks(); mocks.session.customer = {customer_id:"c1", full_name:"Ali"}; mocks.session.ready=true; vi.mocked(api.chat).mockResolvedValue(response); });
afterEach(cleanup);
function send(text="Options dikha dein") { fireEvent.change(screen.getByLabelText("Message Sara"), {target:{value:text}}); fireEvent.click(screen.getByText("Send")); }
it("redirects unauthenticated visitors and waits for auth", () => {
  mocks.session.customer=null; render(<Sara/>); expect(mocks.router.replace).toHaveBeenCalledWith("/start"); expect(screen.queryByText("Send")).toBeNull();
});
it("submits messages, shows backend cards and retains conversation ID", async () => {
  render(<Sara/>); send(); await screen.findByText("Verified home");
  expect(api.chat).toHaveBeenCalledWith("Options dikha dein",undefined);
  send("Second wali"); await waitFor(()=>expect(api.chat).toHaveBeenLastCalledWith("Second wali","chat1"));
});
it("shows loading and prevents double send", async () => {
  let finish!: (value: typeof response)=>void;
  vi.mocked(api.chat).mockReturnValue(new Promise(resolve=>{finish=resolve}));
  render(<Sara/>); send(); expect(screen.getByText("Sending…")).toBeDisabled(); expect(screen.getByRole("status")).toHaveTextContent("preparing");
  finish(response); await screen.findByText("Verified home"); expect(api.chat).toHaveBeenCalledTimes(1);
});
it("displays a safe error and keeps the draft", async () => {
  vi.mocked(api.chat).mockRejectedValue(new ApiError("provider secret",503)); render(<Sara/>); send();
  expect(await screen.findByRole("alert")).toHaveTextContent("could not complete"); expect(screen.queryByText(/provider secret/)).toBeNull(); expect(screen.getByLabelText("Message Sara")).toHaveValue("Options dikha dein");
});
it.each([['Like','liked'],['Reject','rejected'],['Shortlist','shortlisted']])("%s uses owned feedback with the returned session", async (button,action) => {
  vi.mocked(api.recordMyInteraction).mockResolvedValue({interaction_id:'i1'}); render(<Sara/>); send(); await screen.findByText("Verified home"); fireEvent.click(screen.getByText(button));
  await waitFor(()=>expect(api.recordMyInteraction).toHaveBeenCalledWith('p1',action,'rec1'));
});
it("opens the existing booking form", async () => {
  render(<Sara/>); send(); await screen.findByText("Verified home"); fireEvent.click(screen.getByText("Book visit")); expect(screen.getByText("Confirm visit")).toBeInTheDocument();
});
it("new chat clears the conversation ID", async () => {
  render(<Sara/>); send(); await screen.findByText("Verified home"); fireEvent.click(screen.getByText("New chat")); send("New options"); await waitFor(()=>expect(api.chat).toHaveBeenLastCalledWith("New options",undefined));
});
it("does not show an old account's in-flight reply after switching accounts", async () => {
  let finish!: (value: typeof response)=>void;
  vi.mocked(api.chat).mockReturnValue(new Promise(resolve=>{finish=resolve}));
  const view=render(<Sara/>); send(); mocks.session.customer={customer_id:"c2",full_name:"Other"}; view.rerender(<Sara/>);
  finish(response); await waitFor(()=>expect(screen.queryByText("Sending…")).toBeNull()); expect(screen.queryByText("Verified home")).toBeNull();
});
it("waits for authentication before showing the input", () => {
  mocks.session.ready=false; render(<Sara/>); expect(screen.getByRole("status")).toHaveTextContent("Checking"); expect(screen.queryByLabelText("Message Sara")).toBeNull();
});
