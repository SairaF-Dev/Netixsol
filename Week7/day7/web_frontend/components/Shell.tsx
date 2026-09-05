"use client";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { useSession } from "./SessionProvider";

const links = [["/", "Home"], ["/properties", "Properties"], ["/recommendations", "Recommendations"], ["/preferences", "Preferences"], ["/appointments", "Appointments"], ["/sara", "Sara"]];
export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname(); const { customer, switchCustomer } = useSession();
  return <div className="app-shell"><aside className="sidebar"><Link href="/" className="brand"><span>S</span><div>Sara<small>Real Estate</small></div></Link><nav>{links.map(([href,label]) => <Link key={href} href={href} className={pathname===href?"active":""}>{label}</Link>)}</nav><div className="session-card"><small>Development customer</small><strong>{customer?.full_name || "Not selected"}</strong>{customer && <button className="link-button" onClick={switchCustomer}>Switch customer</button>}</div></aside><main><header className="topbar"><div><small>VERIFIED PROPERTY EXPERIENCE</small><b>{customer ? `Welcome, ${customer.full_name?.split(" ")[0] || "Customer"}` : "Development session"}</b></div><span className="verified">● Verified data</span></header><div className="page">{children}</div></main></div>;
}
