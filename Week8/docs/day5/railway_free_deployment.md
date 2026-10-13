# Railway Free deployment guide

This is a manual setup guide for the Week 7 + Week 8 monorepo. It does not contain credentials. Add all secrets in Railway service variables, not in Git or chat.

The public repository intentionally excludes property and lead data files. The Week 8 property catalog contains listing dates from 2018–2019, so it is imported only as historical, unavailable reference data. The migration archives older listings and preserves CRM records; it does not create placeholder agent contacts. Public property search remains empty until current listings with redistribution rights are supplied and reviewed.

## Cost and runtime limits

Railway's current [pricing page](https://railway.com/pricing) lists a no-card Free Trial with a one-time $5 credit for 30 days, followed by the Free plan with $1/month in usage credit and a 0.5 GB per-service memory limit. This is a small demo allowance, not free 24/7 hosting for six running services. Watch Railway usage and stop services that are not needed; do not add a payment method or upgrade if the requirement is strictly no-charge. Vapi credits are separate from Railway usage.

Railway Free and Trial plans block outbound SMTP. This deployment uses the Google Apps Script HTTPS email relay instead. See the [outbound networking and email delivery policy](https://docs.railway.com/networking/outbound-networking). A personal Gmail Apps Script account is currently limited to 100 email recipients per day; see [Google's quota table](https://developers.google.com/apps-script/guides/services/quotas).

## Create the services

Create one Railway project and create these application services from the same GitHub repository. Use Neon for PostgreSQL so the database does not consume a Railway service slot. Set each service's **Root Directory** and build configuration as shown:

| Railway service | Root Directory | Build configuration | Health path |
|---|---|---|---|
| `Week8API` | `/Week8` | Dockerfile at the root | `/health` |
| `Week7API` | `/Week7` | Dockerfile path `day7/web_api/Dockerfile` | `/health` |
| `Day4API` | `/Week7/day4` | Dockerfile at the root | `/health` |
| `VapiWebhook` | `/Week7` | Dockerfile path `day7/vapi_integration/Dockerfile` | `/health` |
| `Website` | `/Week7/day7/web_frontend` | Railpack/Node.js; `npm ci`, then `npm run build` | `/` |

For `Week7API` and `VapiWebhook`, set `RAILWAY_DOCKERFILE_PATH` to the path in the table. Their Docker build context must remain `/Week7`, because the images copy sibling Week 2–4 and Week 7 source directories. The repository's `Week7/.dockerignore` excludes local `.env` files, credential files, caches and frontend build artifacts from that context. Railway's [monorepo guide](https://docs.railway.com/deployments/monorepo) documents service root directories; its [Dockerfile guide](https://docs.railway.com/builds/dockerfiles) documents custom Dockerfile paths.

All three Python container entry points now listen on Railway's injected `PORT` (with local defaults retained). The `Week7API` container already did this. Set the health path in Railway's deployment settings; Railway checks it during deployment, not continuously.

## Connect Neon and internal services

Use Railway's private network for service-to-service calls. Create a Neon project and set its pooled PostgreSQL connection string as the `DATABASE_URL` secret in the Variables tab of each listed service. Require TLS (`sslmode=require`) and do not commit or paste the URL into chat. Neon is external to Railway, so do not use a Railway `${{Postgres.*}}` variable reference.

| Service | Variable | Value |
|---|---|---|
| `Week7API` | `DATABASE_URL` | Neon pooled connection string (secret) |
| `Day4API` | `DATABASE_URL` | Neon pooled connection string (secret) |
| `VapiWebhook` | `DATABASE_URL` | Neon pooled connection string (secret) |
| `Week7API` | `DAY4_API_URL` | `http://${{Day4API.RAILWAY_PRIVATE_DOMAIN}}:${{Day4API.PORT}}` |
| `VapiWebhook` | `DAY4_API_URL` | `http://${{Day4API.RAILWAY_PRIVATE_DOMAIN}}:${{Day4API.PORT}}` |
| `VapiWebhook` | `WEEK8_API_URL` | `http://${{Week8API.RAILWAY_PRIVATE_DOMAIN}}:${{Week8API.PORT}}` |
| `VapiWebhook` | `SARA_WEB_API_INTERNAL_URL` | `http://${{Week7API.RAILWAY_PRIVATE_DOMAIN}}:${{Week7API.PORT}}` |

Railway documents [variable references](https://docs.railway.com/variables) and [private networking](https://docs.railway.com/networking/private-networking). Neon documents [connection strings](https://neon.tech/docs/connect/connect-from-any-app) and pooled connections.

Set the same newly generated `DAY4_API_KEY` value on `Day4API`, `Week7API`, and `VapiWebhook`. Set `Week7API` variables `SARA_ENV=production` and `SARA_AUTH_SECURE_COOKIE=1`. After generating the public `Website` domain, set `SARA_WEB_CORS_ORIGINS` on `Week7API` to that exact HTTPS origin.

## Configure Google Calendar and free email

On `Day4API`, set:

```text
APP_ENV=production
CALENDAR_BACKEND=google
GOOGLE_SERVICE_ACCOUNT_JSON=<service-account JSON secret>
GOOGLE_CALENDAR_ID=<calendar ID>
EMAIL_BACKEND=google_apps_script
GOOGLE_APPS_SCRIPT_URL=<deployed Apps Script /exec URL>
GOOGLE_APPS_SCRIPT_TOKEN=<same secret stored in Apps Script Script Properties>
DAY4_API_KEY=<shared internal key>
```

Store the complete service-account JSON as a Railway secret variable; the Day 4 calendar gateway accepts this JSON directly and does not require a credential file. Share the calendar with the service-account email and grant event-edit permissions.

Set these same three email variables on `VapiWebhook`, plus `EMPLOYEE_EMAIL`. The Apps Script script is at `Week7/day4/scripts/gmail_email_relay.gs`. Deploy it to execute as the Gmail owner, set its `RELAY_TOKEN` Script Property, authorize sending, and use its `/exec` URL. Do not set `SMTP_*` variables on the Free plan.

## Public URLs, frontend and Vapi

Generate public domains for `Week8API`, `Week7API`, `VapiWebhook`, and `Website`. Keep Day 4 and PostgreSQL private. Then set:

| Service | Variable | Value |
|---|---|---|
| `Week8API` | `CORS_ALLOWED_ORIGINS` | Exact HTTPS `Website` origin |
| `Week7API` | `SARA_WEB_CORS_ORIGINS` | Exact HTTPS `Website` origin |
| `Website` | `NEXT_PUBLIC_WEEK8_API_URL` | Public HTTPS `Week8API` URL |
| `Website` | `NEXT_PUBLIC_SARA_API_URL` | Public HTTPS `Week7API` URL |
| `Website` | `NEXT_PUBLIC_VAPI_PUBLIC_KEY` | Vapi public client key |
| `VapiWebhook` | `VAPI_WEBHOOK_SECRET` | Secret configured in the Vapi webhook |

Next.js `NEXT_PUBLIC_*` variables are embedded during the frontend build, so trigger a redeploy after setting or changing them. Configure the Vapi assistant's server/webhook URL as the public `VapiWebhook` URL and its secret header to match `VAPI_WEBHOOK_SECRET`. If using the assistant setup script, also set `VAPI_API_KEY` and `VAPI_ASSISTANT_ID` only in the private service environment.

## Private historical property catalog

The Week 7 API creates its schema at startup, and Day 4 initializes its tables. No property or lead CSVs are included in the public repository. The property catalog contains 190,772 records: 190,731 imported records plus 41 pre-existing records. The imported CSV has `date_added` values from 2018–2019 and does not include a current-availability field. All catalog records remain browseable, but are not marked currently available. The website warns customers that prices and availability may have changed and should be confirmed.

Keep the private property file outside Git, allowlist your current IP in Neon if needed, and run the migration from the repository root with a local `DATABASE_URL` and `WEEK8_CSV_PATH`:

```powershell
$env:WEEK8_CSV_PATH = (Resolve-Path "C:\private-data\properties_clean.csv").Path
& "Week8\.venv\Scripts\python.exe" "Week7\day7\web_api\scripts\migrate_week8_catalog.py"
Remove-Item Env:WEEK8_CSV_PATH
Remove-Item Env:DATABASE_URL
```

Set `DATABASE_URL` in the local PowerShell environment without putting its value in command history or sharing it. The migration prints aggregate counts only, retains older property records, marks the imported catalog historical/unavailable, and preserves user/CRM records. Remove any temporary Neon IP allowlist entry after seeding.

Finally, verify `/health` on the four APIs, register and sign in through the website, get a Week 8 valuation and lead score, and perform a real appointment booking/reschedule/cancel. Property search requires the optional catalog to be imported. Confirm both agent and customer email delivery, the Google Calendar event, and a Vapi hot-lead alert. A green health check does not prove those external operations work.

## Known demo limitations

- The Free allowance may not keep five web services and PostgreSQL running continuously; the site may become unavailable after included usage is consumed.
- A Free deployment is for a demo, not a production availability promise. Railway health checks only gate a new deployment.
- Gmail Apps Script quota is shared by all scripts on the sender account and counts recipients, not just requests.
- Week 8 valuation still misses the assignment's <15% MAPE target, and lead labels are simulated. Do not represent those model results as validated CRM performance.
