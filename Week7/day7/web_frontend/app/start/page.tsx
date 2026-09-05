"use client";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";

export default function Start(){
  const {setCustomer}=useSession(); const router=useRouter();
  const [mode,setMode]=useState<"login"|"register">("login"); const [busy,setBusy]=useState(false); const [error,setError]=useState("");
  const submit=async(e:React.FormEvent<HTMLFormElement>)=>{e.preventDefault();setBusy(true);setError("");const data=new FormData(e.currentTarget);try{const email=String(data.get("email"));const password=String(data.get("password"));const user=mode==="login"?await api.login({email,password}):await api.register({full_name:String(data.get("name")),phone:String(data.get("phone")),email,password});setCustomer(user);router.push("/");}catch(e){setError(e instanceof ApiError?e.message:"Authentication could not be completed.");}finally{setBusy(false)}};
  return <section className="onboarding"><div><span className="eyebrow">SECURE CUSTOMER SESSION</span><h1>Your next address<br/><em>starts here.</em></h1><p>Sign in to access only your own preferences, recommendations, feedback and appointments.</p></div><form className="panel" onSubmit={submit}><div className="card-actions"><button type="button" className={mode==="login"?"primary":""} onClick={()=>setMode("login")}>Login</button><button type="button" className={mode==="register"?"primary":""} onClick={()=>setMode("register")}>Register</button></div><h2>{mode==="login"?"Welcome back":"Create account"}</h2>{mode==="register"&&<><label>Full name<input name="name" required minLength={2} autoComplete="name"/></label><label>Phone<input name="phone" required autoComplete="tel" placeholder="0300 1234567"/></label></>}<label>Email<input name="email" type="email" required autoComplete="email"/></label><label>Password<input name="password" type="password" required minLength={mode==="register"?10:1} autoComplete={mode==="login"?"current-password":"new-password"}/></label><button className="primary" disabled={busy}>{busy?"Please wait…":mode==="login"?"Login":"Register"}</button>{error&&<div role="alert" className="notice error">{error}</div>}<small>Authentication uses a secure HttpOnly backend session cookie. Passwords are never stored in this browser.</small></form></section>
}
