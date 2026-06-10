# Payment Live Readiness - 2026-06-07

## Verdict

The self-serve payment and delivery code path is test-green, but production launch is blocked by external/runtime readiness.

Last redacted command:

```powershell
python payment_server.py readiness-check
```

Status: `blocked`

## Current Blockers

1. `base_url_tls_invalid`
   - `https://duesight.nl` presents a certificate for `*.hostnetbv.nl`, not `duesight.nl`.
   - `curl -I https://duesight.nl` fails with hostname mismatch.

2. `webhook_tls_invalid`
   - Same hostname mismatch applies to `https://duesight.nl/api/payment/webhook`.
   - Mollie webhooks should not be pointed here until TLS is valid.

3. `payment_service_unreachable`
   - `https://duesight.nl/health` returns `404`.
   - `https://duesight.nl/api/payment/products` returns `404`.

4. `local_payment_service_unreachable`
   - `http://127.0.0.1:5051/health` is not reachable in the current local runtime.

5. `smtp_not_ready`
   - `DUESIGHT_EMAIL_SEND_ENABLED=false`.
   - SMTP config is not present in the current environment.

6. `payment_admin_secret_missing`
   - Internal payment mutation endpoints require `DUESIGHT_PAYMENT_ADMIN_SECRET`.
   - Do not mount `/api/payment/*` publicly without this secret configured in the runtime.

7. `pm2_missing`
   - `pm2` / `pm2.cmd` is not available on PATH.
   - Required process names are `duesight-payment` and `duesight-delivery-worker`.

## Verified Green

- Payment/delivery unit and E2E suite:

```powershell
python -m pytest tests\test_checkout_terms.py tests\test_delivery_flow.py tests\test_payment_webhook.py tests\test_order_uploads.py tests\test_refund_flow.py tests\test_payment_e2e_flow.py -q
```

Result after upload-return, admin-secret, email/refund smoke coverage: `55 passed`

- Redacted readiness CLI exists:

```powershell
python payment_server.py readiness-check --skip-network --skip-pm2 --skip-local-service
```

- Redacted PowerShell wrapper exists:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\payment_live_readiness.ps1 -SkipNetwork -SkipPm2 -SkipLocalService
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\payment_live_readiness.ps1 -SkipNetwork -SkipPm2 -StartLocalService
```

- Redacted operational smokes exist:

```powershell
python payment_server.py email-smoke --to controlled@example.test
python payment_server.py refund-smoke --order-id <paid-order-id>
```

- Delivery now stays paid-only: refunded/cancelled orders are rejected by the admin delivery endpoint, direct worker call, and queue selector.
- Delivery event logs redact token query values; the usable tokenized link is kept only in the order row and e-mail/outbox path needed for delivery.
- Customer uploads are accepted only while an order is still open for input; refunded/cancelled/failed/delivered orders reject new uploads.
- Customer uploads are limited per order through `DUESIGHT_MAX_UPLOADS_PER_ORDER` and per file through `DUESIGHT_MAX_UPLOAD_BYTES`.
- Stale uploads for abandoned/non-delivered non-paid orders can be audited with `python payment_server.py cleanup-uploads` and purged only with explicit `--execute`; default retention is `DUESIGHT_STALE_UPLOAD_RETENTION_HOURS`.
- `cleanup-uploads` CLI output redacts order IDs and reports counts only.

- Local payment API route smoke is green when the service is started with the explicit `serve` subcommand:

```powershell
python payment_server.py serve --host 127.0.0.1 --port 5051
python payment_server.py readiness-check --skip-network --skip-pm2
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\payment_live_readiness.ps1 -SkipNetwork -SkipPm2 -StartLocalService
```

Observed local result: `/health` and `/api/payment/products` return HTTP 200 JSON. With `DUESIGHT_PAYMENT_ADMIN_SECRET` configured, only `smtp_not_ready` remains when network and PM2 checks are skipped.

- Launch env template exists:

```powershell
.env.example
```

It contains placeholders only, no real secrets, and excludes Docker-only optional stacks from the standard launch path.

## Fix Order

1. Fix DNS/TLS for `duesight.nl` and `www.duesight.nl`.
   - Current DNS resolves to `91.184.0.200` and `2a02:2268:1:0:f816:3eff:fe7b:63c6`.
   - `www.duesight.nl` is a CNAME to `duesight.nl`.
   - Certificate currently served is not valid for DueSight.
   - No Cloudflare/Vercel/Netlify/wrangler deploy config was found in this repo. Treat DNS/TLS routing as external/domain-hosting work unless a separate deploy project is provided.

2. Deploy or route the payment API.
   - `/health` must return JSON with `service = "DueSight Payment Server"`.
   - `/api/payment/products` must return the configured product map.

3. Configure runtime process supervision.
   - Install/use PM2 or replace the readiness check with the actual production supervisor.
   - Required process labels: `duesight-payment`, `duesight-delivery-worker`.

4. Configure the payment admin secret.
   - Set `DUESIGHT_PAYMENT_ADMIN_SECRET` to a long random value in the payment-server runtime.
   - Use `X-DueSight-Admin-Secret` or `Authorization: Bearer <secret>` only for internal delivery/refund operations.
   - Keep customer endpoints, Mollie webhook, upload, email-gated status, and tokenized report links public as designed.
   - `/api/payment/status/{order_id}` requires the order e-mail as `customer_email`; do not record customer data in smoke notes.

5. Configure SMTP for real delivery.
   - Enable `DUESIGHT_EMAIL_SEND_ENABLED=true`.
   - Provide SMTP host/user/pass through environment or production secret store.

6. Only then switch from test to live Mollie.
   - The readiness output should show `mollie_key_mode = live`.
   - Do not enable live webhooks before TLS and route probes are green.

## Final Gate

Use:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts\payment_live_readiness.ps1 -RequireReady
```

Expected result before launch: exit `0`, `status = ready`, no blockers.
