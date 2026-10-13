"use client";
import { createContext, useContext, useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { api } from "@/lib/api";
import type { Customer, UserRole } from "@/types/api";

type Session = {
  customer: Customer | null;
  ready: boolean;
  role: UserRole;
  setRole: (role: UserRole) => void;
  setCustomer: (value: Customer) => void;
  switchCustomer: () => void;
};
const Context = createContext<Session | null>(null);

const STORAGE_KEY = "sara_user_role";

export function SessionProvider({ children }: { children: React.ReactNode }) {
  const [customer, update] = useState<Customer | null>(null);
  const [role, setRoleState] = useState<UserRole>("customer");
  const [ready, setReady] = useState(false);
  const router = useRouter();

  useEffect(() => {
    try {
      const saved = localStorage.getItem(STORAGE_KEY);
      if (saved === "customer" || saved === "sales_agent") {
        setRoleState(saved);
      }
    } catch {
      // Safe fallback if localStorage is restricted
    }
    api.me().then(update).catch(() => update(null)).finally(() => setReady(true));
  }, []);

  const setRole = (value: UserRole) => {
    setRoleState(value);
    try {
      localStorage.setItem(STORAGE_KEY, value);
    } catch {
      // Safe fallback if localStorage write fails
    }
  };

  const setCustomer = (value: Customer) => { update(value); };
  const switchCustomer = () => { void api.logout().finally(() => { update(null); router.push("/start"); }); };

  return (
    <Context.Provider value={{ customer, ready, role, setRole, setCustomer, switchCustomer }}>
      {children}
    </Context.Provider>
  );
}

export function useSession() {
  const value = useContext(Context);
  if (!value) throw new Error("SessionProvider missing");
  return value;
}

