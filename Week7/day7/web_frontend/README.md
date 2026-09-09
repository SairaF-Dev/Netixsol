# Sara Real Estate Development Frontend — Phase 9

Next.js App Router + TypeScript frontend for the authenticated shared FastAPI.
It contains no backend credentials, ML implementation, fabricated property
photos, or fake chat. Browser voice reuses the existing VAPI assistant.

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
npm.cmd install
npm.cmd run dev
```

Open `http://localhost:3000`.

Keep the existing `.env.local`; it needs `NEXT_PUBLIC_SARA_API_URL` and
`NEXT_PUBLIC_VAPI_PUBLIC_KEY`. Never put the private VAPI key in this file.
On `/sara`, sign in and select **Start voice call**, then allow microphone access.
Mute and end controls are available during the call. HTTPS or localhost is
required for browser microphone access.

Restart the website API and VAPI webhook service after updating the code.
The website API initializes the additive voice-session table on startup.
The webhook forwards browser events to `SARA_WEB_API_INTERNAL_URL`
(default `http://localhost:8010`); both services need the same PostgreSQL database
and `VAPI_WEBHOOK_SECRET`. Keep the existing assistant ID and server configuration.
See [browser voice verification](../../docs/BROWSER_VOICE_REPORT.md).

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
