"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Customer } from "@/types/api";

type Session = { customer: Customer | null; ready: boolean; setCustomer: (value: Customer) => void; switchCustomer: () => void };
const Context = createContext<Session | null>(null);

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [customer, update] = useState<Customer | null>(null);
  const [ready, setReady] = useState(false);
  const router = useRouter();
  useEffect(() => { api.me().then(update).catch(()=>update(null)).finally(()=>setReady(true)); }, []);
  const setCustomer = (value: Customer) => { update(value); };
  const switchCustomer = () => { void api.logout().finally(()=>{ update(null); router.push("/start"); }); };
  return <Context.Provider value={{ customer, ready, setCustomer, switchCustomer }}>{children}</Context.Provider>;
}
export function useSession() { const value = useContext(Context); if (!value) throw new Error("SessionProvider missing"); return value; }
