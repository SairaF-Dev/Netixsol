# Day 5 operations and handover

## Runtime and health

The FastAPI service loads valuation and lead artifacts at startup. `GET /health` reports model readiness; `GET /model/info` reports model versions and locked metrics. The assistant works without an LLM key using its deterministic, tool-grounded response path. If an LLM provider is enabled, supply its key through the runtime secret manager, never in source control or the image.

## Drift monitoring

Run `python -m src.mlops.monitoring` after each labeled data refresh and at least monthly. It compares the train reference population against current rows using Population Stability Index (PSI): values at or above 0.10 warn, and values at or above 0.25 are critical. For labeled current data it also computes MAPE and alerts above the assignment target of 15%. Reports are written to `reports/day5/drift_report.json`.

To verify the alert path without changing source data, use:

```powershell
python -m src.mlops.monitoring --simulate-price-increase 0.15 --output reports\day5\simulated_drift_report.json
```

The simulation alters only the in-memory monitoring sample. It does not overwrite the input data. An alert requests review; it does not by itself promote a model.

## Valuation explanations

The API returns local TreeSHAP attributions for Sale and Rent predictions. To generate a population-level summary plot and a local waterfall from the matching validation split, run:

```powershell
python -m src.models.explain_valuation --purpose sale
python -m src.models.explain_valuation --purpose rent
```

The report, global summary plot, and local waterfall are written to `reports/figures/day3/`. Attribution values describe changes in model log-price, not separate PKR adjustments.

## Retraining, approval and rollback

Refresh the purpose-specific training and validation CSVs with quality-checked, labeled observations, then run:

```powershell
python -m src.mlops.retrain --purpose sale
python -m src.mlops.retrain --purpose rent
```

The script fits on the training partition, compares the candidate and active artifacts on validation MAPE, and promotes only a strict improvement. Every promotion saves both prior artifacts in `models/rollback/<UTC timestamp>/`. Restore with:

```powershell
python -m src.mlops.retrain --purpose sale --rollback models\rollback\<UTC timestamp>
```

Schedule monitoring monthly and retraining monthly or after a reviewed drift/performance alert, only after new labeled data is available. Keep the locked test set untouched for final certification. Review metrics, subgroup behavior, source provenance and the model card before exposing a promoted artifact.

## Docker deployment

Build from the Week 8 project root after the processed serving datasets and `.joblib` model artifacts are present:

```powershell
docker build -t netixsol-week8:latest .
docker run --rm -p 8000:8000 `
  -e CORS_ALLOWED_ORIGINS=http://localhost:3000 `
  -e OPENAI_API_KEY `
  netixsol-week8:latest
```

`OPENAI_API_KEY` is optional; the deterministic assistant does not need it. Supply it as a runtime secret if required. For deployment, set `CORS_ALLOWED_ORIGINS` to the exact public frontend origins and configure the browser-side `NEXT_PUBLIC_WEEK8_API_URL` to the reachable API URL. Protect the API with the platform's authentication/network controls before making it public; the assignment API is not an authenticated public service.

The container health check calls `/health`. Persist or export `logs/prediction_audit.jsonl` and `reports/day5/` if those records must outlive a container restart; the local append-only audit log is not a substitute for centralized production observability.

## Week 7 live integrations

The Week 8 container alone does not run the Week 7 website, voice webhook, or appointment workflows. For the complete product, deploy those services and the frontend as separate services, with a shared managed PostgreSQL database for the Week 7 application and Day 4 appointment service. Configure the services with the platform's secret manager; do not copy local `.env` files or credential JSON into a container image.

The Day 4 appointment service must run with `APP_ENV=production` and provide `DATABASE_URL`, `CALENDAR_BACKEND=google`, either `GOOGLE_SERVICE_ACCOUNT_FILE` (a mounted secret file) or `GOOGLE_SERVICE_ACCOUNT_JSON` (a secret environment variable), `GOOGLE_CALENDAR_ID`, and `DAY4_API_KEY`. Share the intended Google calendar with the service-account identity and grant it permission to create/update events.

For a no-cost host that does not permit outbound SMTP, use the Gmail Apps Script HTTPS relay included at `Week7/day4/scripts/gmail_email_relay.gs`:

1. Create an Apps Script project while signed into the Gmail account that should send the notifications, then add the relay script.
2. In **Project Settings > Script properties**, set `RELAY_TOKEN` to a long random value.
3. Deploy the script as a **Web app**, choose **Execute as me**, and allow access to **Anyone** so the backend can call it without a Google sign-in session. Authorize the script's email permission and copy the deployed `/exec` URL. See Google's [web app deployment guide](https://developers.google.com/apps-script/guides/web).
4. Set `EMAIL_BACKEND=google_apps_script`, `GOOGLE_APPS_SCRIPT_URL`, and `GOOGLE_APPS_SCRIPT_TOKEN` in both the Day 4 and voice webhook service environments. Keep the token secret; never put it in source control or the browser.

The relay sends as the Gmail account that owns the Apps Script deployment. A consumer Gmail account currently has a documented Apps Script quota of 100 email recipients per day; this is shared with other scripts using that account and can change. See Google's [Apps Script quotas](https://developers.google.com/apps-script/guides/services/quotas). The relay checks that Google confirms each send and returns a workflow warning on failure. For a host that permits SMTP, the existing `EMAIL_BACKEND=smtp` path remains available with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, and `SMTP_SENDER`.

Production startup fails explicitly when the selected backend is missing required settings or is configured to use in-memory providers. Send test booking, rescheduling, cancellation, employee-email, customer-email, and hot-lead alert transactions after deployment; a successful API health check alone does not verify those external providers.

For a no-card Railway setup, see the [Railway Free deployment guide](railway_free_deployment.md), including private service URLs, the shared PostgreSQL setup, the one-time catalog seed, and Free-plan limits.

Connect the Week 7 web API to the appointment service using `DAY4_API_URL` and the same `DAY4_API_KEY` configured on that service. Set `WEEK8_API_URL` for the voice lead scorer and `EMPLOYEE_EMAIL` to enable hot-lead alerts. The voice webhook uses the same `EMAIL_BACKEND` and Google Apps Script relay settings as Day 4, or its configured SMTP credentials when using SMTP. The frontend also needs its public Week 8 API URL and the production API CORS allowlist. Configure Vapi's production webhook URL and webhook secret in the Vapi dashboard and the voice service. Never paste or commit secret values.

## Week 7 connection and data readiness

Week 7's voice webhook calls `POST /predict/lead-score` after a call and can alert an employee for Hot leads. The Week 7 ML web client consumes the Week 8 valuation, lead scoring, explanation, assistant and market endpoints. Its lead demo can also show generated Week 8 sample leads; these are not verified CRM identities. The current lead classifier is trained on simulated labels, so do not use its output for consequential decisions or claim validated CRM accuracy until real, consented CRM outcomes are reviewed and the model is recalibrated.

## Handover checklist

- Start the API and confirm `/health` is healthy.
- Verify both Sale and Rent price predictions, lead scoring, both explanation routes, CSV batch, market stats and assistant chat.
- Review the latest drift report and locked test metrics.
- Confirm the appropriate model card and estimate disclaimer are visible to agents.
- Confirm API URL, CORS origins, authentication and secrets are configured for the target environment.
- Record the approved model version, validation report, rollback directory and deployment date.
