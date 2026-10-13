"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { useSession } from "@/components/SessionProvider";

export default function Start() {
  const { setCustomer } = useSession();
  const router = useRouter();

  const [mode, setMode] = useState<"login" | "register">("login");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  const submit = async (e: React.FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setBusy(true);
    setError("");

    const data = new FormData(e.currentTarget);
    try {
      const email = String(data.get("email"));
      const password = String(data.get("password"));

      const user =
        mode === "login"
          ? await api.login({ email, password })
          : await api.register({
              full_name: String(data.get("name")),
              phone: String(data.get("phone")),
              email,
              password,
            });

      setCustomer(user);
      router.push("/");
    } catch (err) {
      setError(
        err instanceof ApiError ? err.message : "Authentication could not be completed. Please try again."
      );
    } finally {
      setBusy(false);
    }
  };

  return (
    <section className="onboarding">
      <div>
        {/* <span className="eyebrow"></span> */}
        <h1>
          Your next address
          <br />
          <em>starts here.</em>
        </h1>
        <p>
          Sign in to access your saved properties, scheduled visits, and personalized recommendations.
        </p>
      </div>

      <form className="panel" onSubmit={submit}>
        <div className="card-actions">
          <button
            type="button"
            className={mode === "login" ? "primary" : ""}
            onClick={() => {
              setMode("login");
              setError("");
            }}
          >
            Sign In
          </button>
          <button
            type="button"
            className={mode === "register" ? "primary" : ""}
            onClick={() => {
              setMode("register");
              setError("");
            }}
          >
            Create Account
          </button>
        </div>

        <h2>{mode === "login" ? "Welcome back" : "Create an account"}</h2>

        {mode === "register" && (
          <>
            <label>
              Full name
              <input
                name="name"
                required
                minLength={2}
                autoComplete="name"
                placeholder="e.g. Ali Khan"
              />
            </label>
            <label>
              Phone
              <input
                name="phone"
                required
                autoComplete="tel"
                placeholder="0300 1234567"
              />
            </label>
          </>
        )}

        <label>
          Email address
          <input
            name="email"
            type="email"
            required
            autoComplete="email"
            placeholder="name@example.com"
          />
        </label>

        <label>
          Password
          <input
            name="password"
            type="password"
            required
            minLength={mode === "register" ? 8 : 1}
            autoComplete={mode === "login" ? "current-password" : "new-password"}
            placeholder="••••••••"
          />
        </label>

        <button type="submit" className="primary" disabled={busy}>
          {busy ? "Please wait…" : mode === "login" ? "Sign In" : "Get Started"}
        </button>

        {error && (
          <div role="alert" className="notice error">
            {error}
          </div>
        )}

        <small>
          Protected by industry-standard encryption. By continuing, you agree to our Terms of Service and Privacy Policy.
        </small>
      </form>
    </section>
  );
}
