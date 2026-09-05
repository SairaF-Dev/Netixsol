import { beforeEach, expect, it, vi } from "vitest";
import { api } from "@/lib/api";

const response = (body: unknown, status=200, headers?:HeadersInit) => Promise.resolve(new Response(status===204?null:JSON.stringify(body),{status,headers:{"Content-Type":"application/json",...headers}}));
beforeEach(()=>{vi.restoreAllMocks();localStorage.clear()});

it("registers without storing password or customer ownership in localStorage",async()=>{
  const fetchMock=vi.spyOn(globalThis,"fetch").mockImplementation(()=>response({customer_id:"c1",full_name:"Ali",email:"a@example.com",phone:"+92300"},201));
  await api.register({full_name:"Ali",email:"a@example.com",phone:"0300",password:"StrongPass1"});
  expect(fetchMock.mock.calls[0][0]).toContain("/api/auth/register");
  expect(fetchMock.mock.calls[0][1]?.credentials).toBe("include");
  expect(localStorage.length).toBe(0);
});

it("logs in, restores current user, and logs out through cookie endpoints",async()=>{
  const fetchMock=vi.spyOn(globalThis,"fetch").mockImplementation((url)=>String(url).endsWith("logout")?response(null,204):response({customer_id:"c1",full_name:"Ali",email:"a@example.com",phone:null}));
  await api.login({email:"a@example.com",password:"StrongPass1"});
  expect((await api.me()).customer_id).toBe("c1");
  await api.logout();
  expect(fetchMock.mock.calls.map(x=>String(x[0]))).toEqual(expect.arrayContaining([expect.stringContaining("/login"),expect.stringContaining("/me"),expect.stringContaining("/logout")]));
});

it("uses authenticated me endpoints without sending customer UUID",async()=>{
  const fetchMock=vi.spyOn(globalThis,"fetch").mockImplementation(()=>response({customer_id:"c1",amenities:[]}));
  await api.getMyPreferences();
  await api.getMyRecommendations("r1");
  await api.recordMyInteraction("p1","liked","r1");
  const calls=fetchMock.mock.calls.map(x=>({url:String(x[0]),body:String(x[1]?.body||"")}));
  expect(calls.every(x=>x.url.includes("/api/me/"))).toBe(true);
  expect(calls.every(x=>!x.body.includes("customer_id"))).toBe(true);
});

it("returns a safe generic login error",async()=>{
  vi.spyOn(globalThis,"fetch").mockImplementation(()=>response({detail:"Invalid email or password"},401));
  await expect(api.login({email:"a@example.com",password:"wrong"})).rejects.toMatchObject({message:"Invalid email or password",status:401});
});
