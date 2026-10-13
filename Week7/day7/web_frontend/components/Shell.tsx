"use client";
import { useEffect } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useSession } from "./SessionProvider";
import type { UserRole } from "@/types/api";

const ROLE_NAV_LINKS: Record<UserRole, [string, string][]> = {
  customer: [
    ["/properties", "Explore"],
    ["/recommendations", "Recommendations"],
    ["/appointments", "Visits"],
    ["/sara", "Ask Sara"],
  ],
  sales_agent: [
    ["/ml/leads", "Lead Pipeline"],
    ["/ml", "Valuation"],
    ["/ml/assistant", "Agent AI"],
    ["/ml/market", "Market Insights"],
  ],
};

const DEFAULT_LANDING: Record<UserRole, string> = {
  customer: "/properties",
  sales_agent: "/ml/leads",
};

const CUSTOMER_PROTECTED_ROUTES = [
  "/properties",
  "/recommendations",
  "/appointments",
  "/sara",
  "/preferences",
];

export function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { customer, ready, role, setRole, switchCustomer } = useSession();

  // Route Access Guard
  useEffect(() => {
    if (!ready) return;

    const isCustomerRoute = CUSTOMER_PROTECTED_ROUTES.some(
      (p) => pathname === p || pathname.startsWith(p + "/")
    );
    const isAgentRoute = pathname === "/ml" || pathname.startsWith("/ml/");

    if (role === "customer" && isAgentRoute) {
      router.replace(DEFAULT_LANDING.customer);
    } else if (role === "sales_agent" && isCustomerRoute) {
      router.replace(DEFAULT_LANDING.sales_agent);
    }
  }, [pathname, role, ready, router]);

  const handleRoleChange = (newRole: UserRole) => {
    if (newRole === role) return;
    setRole(newRole);
    router.push(DEFAULT_LANDING[newRole]);
  };

  const isLinkActive = (href: string) => {
    if (pathname === href) return true;
    if (href !== "/" && href !== "/ml" && pathname.startsWith(href)) return true;
    return false;
  };

  const currentLinks = ROLE_NAV_LINKS[role] || ROLE_NAV_LINKS.customer;

  return (
    <div className="app-shell">
      <aside className="sidebar" style={{ padding: "24px 20px 32px", overflowY: "auto" }}>
        <Link href="/" className="brand">
          <img
            src="/logo.png"
            alt="Real Estate Hub Logo"
            width={38}
            height={42}
            style={{
              width: "38px",
              height: "42px",
              objectFit: "contain",
              display: "block",
              filter: "drop-shadow(0 2px 4px rgba(0, 0, 0, 0.25))",
            }}
          />
          <div>Real Estate Hub</div>
        </Link>

        {/* Active Role Switcher */}
        <div
          style={{ marginTop: "18px", marginBottom: "6px", display: "grid", gap: "6px" }}
          data-testid="role-switcher"
        >
          <span
            style={{
              fontSize: "0.65rem",
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: "#c28b4b",
              fontWeight: 700,
            }}
          >
            Workspace
          </span>
          <div
            style={{
              display: "flex",
              background: "#102520",
              borderRadius: "8px",
              padding: "3px",
              border: "1px solid #36564f",
              gap: "4px",
            }}
          >
            <button
              type="button"
              onClick={() => handleRoleChange("customer")}
              aria-pressed={role === "customer"}
              style={{
                flex: 1,
                padding: "6px 4px",
                fontSize: "0.78rem",
                fontWeight: 700,
                borderRadius: "6px",
                border: role === "customer" ? "1px solid #4a8072" : "1px solid transparent",
                cursor: "pointer",
                background: role === "customer" ? "#2b5e52" : "transparent",
                color: role === "customer" ? "#ffffff" : "#9fb8b1",
                transition: "all 0.15s ease",
              }}
            >
              Customer
            </button>
            <button
              type="button"
              onClick={() => handleRoleChange("sales_agent")}
              aria-pressed={role === "sales_agent"}
              style={{
                flex: 1,
                padding: "6px 4px",
                fontSize: "0.78rem",
                fontWeight: 700,
                borderRadius: "6px",
                border: role === "sales_agent" ? "1px solid #4a8072" : "1px solid transparent",
                cursor: "pointer",
                background: role === "sales_agent" ? "#2b5e52" : "transparent",
                color: role === "sales_agent" ? "#ffffff" : "#9fb8b1",
                transition: "all 0.15s ease",
              }}
            >
              Agent Portal
            </button>
          </div>
        </div>

        <nav style={{ marginTop: "14px" }}>
          {currentLinks.map(([href, label]) => (
            <Link key={href} href={href} className={isLinkActive(href) ? "active" : ""}>
              {label}
            </Link>
          ))}
        </nav>

        {/* Session Card */}
        <div
          className="session-card"
          style={{
            marginTop: "auto",
            paddingTop: "14px",
            paddingBottom: "32px",
            display: "grid",
            gap: "4px",
          }}
        >
          <small style={{ color: "#9fb8b1", fontSize: "0.75rem" }}>Account</small>
          <strong style={{ fontSize: "0.9rem", color: "#f3ede2" }}>
            {customer?.full_name || "Guest User"}
          </strong>

          {customer ? (
            <button
              type="button"
              className="link-button"
              onClick={switchCustomer}
              style={{
                padding: "4px 0",
                color: "#e5c395",
                fontSize: "0.8rem",
                cursor: "pointer",
                display: "inline-block",
                textAlign: "left",
                background: "none",
                border: "none",
              }}
            >
              Sign Out
            </button>
          ) : (
            <Link
              href="/start"
              style={{
                color: "#e5c395",
                fontSize: "0.8rem",
                textDecoration: "none",
                marginTop: "2px",
              }}
            >
              Sign In →
            </Link>
          )}
        </div>
      </aside>

      <main style={{ minHeight: "100vh", overflowY: "auto" }}>
        <div
          className="page"
          style={
            pathname === "/start"
              ? {
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  minHeight: "100vh",
                  padding: "40px 60px",
                }
              : undefined
          }
        >
          {children}
        </div>
      </main>
    </div>
  );
}
