# Sara Website

Next.js App Router and TypeScript frontend for the shared website API. Pages
include login/registration (`/start`), preferences, properties, recommendations,
appointments, and Sara text chat/browser voice (`/sara`).

## Setup and run

Start PostgreSQL and the website API using the [root setup](../../README.md).
Create or update `.env.local` in this directory, preserving existing values:

```env
NEXT_PUBLIC_SARA_API_URL=http://localhost:8010
NEXT_PUBLIC_VAPI_PUBLIC_KEY=
```

Use the VAPI public browser key, never its private key. No `.env.example` is
supplied. Restart the dev server after configuration changes.

From this directory:

```powershell
npm.cmd ci
npm.cmd run dev
```

Open `http://localhost:3000/start`. Use `localhost` for the browser API hostname
as well so development cookies remain same-site. Production requires HTTPS,
backend `SARA_AUTH_SECURE_COOKIE=1`, and appropriate API CORS origins.

## Browser voice

Start the VAPI webhook on 8007 and website API on 8010. Configure the existing
assistant's HTTPS webhook and secret. Both backends need the same PostgreSQL
database and `VAPI_WEBHOOK_SECRET`; the website API needs `VAPI_ASSISTANT_ID`.
The webhook forwards browser events to `SARA_WEB_API_INTERNAL_URL`, defaulting
to `http://localhost:8010`.

Sign in on `/sara`, select **Start voice call**, and allow microphone access.
Start/cancel/end/mute controls use `@vapi-ai/web`. The public key must permit the
site and assistant. See the [browser voice report](../../docs/BROWSER_VOICE_REPORT.md)
for implementation evidence and outstanding live checks.

## State and API boundaries

- Identity is restored through `/api/auth/me` using an HttpOnly session cookie.
  The central `lib/api.ts` client includes cookies and manages CSRF tokens.
- Recommendations retain the returned session ID for feedback; the server
  validates recommendation membership and customer ownership.
- Appointment listings use `/api/me/appointments`.
- Chat uses `/api/me/chat` and retains at most 40 visible messages in component
  memory. Navigation/reload starts a new conversation. Account changes discard
  old state and stale responses.
- Browser calls obtain an authenticated capability. Navigation or account
  replacement stops the call and revokes it.
- Retrieval, preference persistence, ranking, and ML remain on the backend.

## Checks and production build

```powershell
npm.cmd test
npm.cmd run build
npm.cmd start
```

`start` serves a completed production build. Build success does not verify live
VAPI audio or Calendar/email delivery. See the
[troubleshooting guide](../../docs/ADMIN_AND_TROUBLESHOOTING_GUIDE.md).
