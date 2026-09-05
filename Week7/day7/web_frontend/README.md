# Sara Real Estate Development Frontend — Phase 9

Next.js App Router + TypeScript frontend for the authenticated shared FastAPI.
It contains no backend credentials, ML implementation, fabricated property
photos, fake chat, or browser voice.

## Run

Backend:

```powershell
cd E:\Netixsol\Week7\day7
python -m uvicorn web_api.app:app `
    --host 127.0.0.1 `
    --port 8010 `
    --reload
```

Frontend:

```powershell
cd E:\Netixsol\Week7\day7\web_frontend
Copy-Item .env.example .env.local
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

## Boundaries

- Registration/login creates a backend-owned HttpOnly session cookie. The
  browser restores identity through `/api/auth/me`; customer ownership and
  passwords are never stored in localStorage.
- Recommendations create one UUID per explicit load/refresh and retain the
  returned ID with the visible cards for feedback.
- Appointment listings use authenticated `/api/me/appointments` ownership.
- `/sara` uses authenticated `/api/me/chat` via the central CSRF-aware client.
  Cards retain backend recommendation IDs and reuse existing feedback and visit
  components. Chat state stays in component memory (40 messages maximum); a
  reload starts a new conversation. Browser voice remains outside Phase 9.
- All ranking and the synthetic development ML boundary remain server-side.

Use `http://localhost:8010` as the browser API URL so localhost frontend and
backend remain same-site for the `SameSite=Lax` development cookie. Production
must use HTTPS and set `SARA_AUTH_SECURE_COOKIE=1`.
